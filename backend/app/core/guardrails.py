import os
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

logger = logging.getLogger("kerdostat-guardrails")

class GuardrailEngine:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Locate relative to backend root
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(backend_dir, "guardrail_config.json")
            
        self.config_path = config_path
        self.config = {
            "max_position_size": 1000,
            "daily_loss_limit": 5000.0,
            "max_open_trades": 5
        }
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
                logger.info(f"Successfully loaded guardrail config: {self.config}")
            except Exception as e:
                logger.error(f"Error loading guardrail config from {self.config_path}: {e}. Using defaults.")
        else:
            logger.warning(f"Guardrail config file not found at {self.config_path}. Creating default config.")
            try:
                with open(self.config_path, "w") as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to create default config file: {e}")

    def validate_trade(self, symbol: str, qty: int, price: float, db: Session, sl: Optional[float] = None) -> tuple[bool, str]:
        from app.main import ProposalModel, AuditLogModel
        # 1. Max Position Size Check
        if qty > self.config["max_position_size"]:
            return False, f"Trade quantity {qty} exceeds maximum position size limit of {self.config['max_position_size']}."

        # 2. Max Open Trades Check
        open_trades_count = db.query(ProposalModel).filter(ProposalModel.status == "approved").count()
        if open_trades_count >= self.config["max_open_trades"]:
            return False, f"Number of concurrent open trades ({open_trades_count}) is at or exceeds the maximum limit of {self.config['max_open_trades']}."

        # 3. Daily Loss Limit / Drawdown Check
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_logs = db.query(AuditLogModel).filter(
            AuditLogModel.timestamp.like(f"{today_str}%"),
            AuditLogModel.action_type.in_(["APPROVE", "HIJACK_EXECUTE"]),
            AuditLogModel.status == "SUCCESS"
        ).all()

        def get_log_risk(log):
            proposal = db.query(ProposalModel).filter(ProposalModel.symbol == log.symbol).first()
            if not proposal:
                return 0.02 * log.price * log.qty
            
            entry = log.price
            sl_val = proposal.SL
            tp_val = proposal.TP
            
            # If entry and SL are stored as the same value, estimate the entry price from TP and SL
            if abs(entry - sl_val) < 1e-5:
                if tp_val > sl_val:  # BUY
                    entry = sl_val + (tp_val - sl_val) * 0.2
                elif sl_val > tp_val:  # SELL
                    entry = sl_val - (sl_val - tp_val) * 0.2
                else:
                    entry = sl_val * 1.02
                    
            raw_risk = abs(entry - sl_val) * log.qty
            return min(raw_risk, entry * log.qty)

        total_daily_loss = sum(get_log_risk(log) for log in today_logs)
        
        # Estimate risk for the new trade
        new_trade_sl = sl if sl is not None else (price * 0.95)
        raw_new_risk = abs(price - new_trade_sl) * qty
        new_trade_risk = min(raw_new_risk, price * qty)
        
        if total_daily_loss + new_trade_risk > self.config["daily_loss_limit"]:
            return False, (
                f"Trade risk of {new_trade_risk:.2f} would push today's total loss/risk "
                f"({total_daily_loss:.2f}) over the daily limit of {self.config['daily_loss_limit']}."
            )

        return True, ""
