import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.websocket import manager
from app.models.user import UserModel
from app.models.proposal import ProposalModel
from app.models.audit import AuditLogModel
from app.models.state import SystemStateModel
from app.services import select_executor_by_symbol, alpaca_executor, fetch_live_market_data, generate_mock_ohlcv
from app.core.signal_engine import calculate_signals

logger = logging.getLogger("kerdostat-scanner")

def seed_db(db: Session):
    """
    Seeds initial demonstration accounts, proposals, and system modes if empty.
    """
    if db.query(UserModel).count() == 0:
        db.add(UserModel(
            id="user-1",
            name="Alex Mercer",
            email="trader@kerdostat.com",
            password="password123"
        ))
    if db.query(ProposalModel).count() == 0:
        db.add(ProposalModel(
            id="prop-1",
            symbol="QUANT",
            signal="BUY",
            qty=150,
            SL=149.0,
            TP=157.5,
            status="pending",
            XAIReason="Neural network identified a triple-bottom support pattern at $149.50 with a confirmed breakout above the 50-period SMA on the 15-minute timeframe. Relative strength index (RSI) turned upward from oversold boundaries.",
            risk_score=3.2
        ))
        db.add(ProposalModel(
            id="prop-2",
            symbol="NVDA",
            signal="BUY",
            qty=80,
            SL=122.5,
            TP=134.0,
            status="pending",
            XAIReason="Fibonacci retracement level at 0.618 matches historic buying demand zones. Pre-market social sentiment indices show a +82% bullish index bias on news of cloud hardware expansions.",
            risk_score=4.1
        ))
        db.add(ProposalModel(
            id="prop-3",
            symbol="TSLA",
            signal="SELL",
            qty=120,
            SL=183.0,
            TP=173.5,
            status="pending",
            XAIReason="Strong resistance verified at the 200 EMA on the 1-hour timeline. MACD histogram signals a bearish divergence crossover with rising sell volume, suggesting buyers exhaustion.",
            risk_score=5.0
        ))

    if db.query(SystemStateModel).filter(SystemStateModel.key == "mode").count() == 0:
        db.add(SystemStateModel(key="mode", value="copilot"))
    db.commit()

async def run_symbol_scanner():
    """
    Periodic background loop scanning symbols and creating proposals.
    """
    SCAN_SYMBOLS = ["AAPL", "MSFT", "TSLA", "RELIANCE", "TCS", "INFY"]
    scanned_signals = {sym: "HOLD" for sym in SCAN_SYMBOLS}
    logger.info(f"Background scanner initialized for symbols: {SCAN_SYMBOLS}")
    try:
        while True:
            db = SessionLocal()
            try:
                for symbol in SCAN_SYMBOLS:
                    try:
                        candles = fetch_live_market_data(symbol, "1D", alpaca_executor)
                        if not candles or len(candles) < 30:
                            candles = generate_mock_ohlcv(symbol, "1D")
                        
                        result = calculate_signals(candles)
                        new_signal = result["signal"]
                        old_signal = scanned_signals.get(symbol, "HOLD")
                        
                        if new_signal != old_signal:
                            scanned_signals[symbol] = new_signal
                            logger.info(f"[Scanner] Signal changed for {symbol}: {old_signal} -> {new_signal}")
                            
                            event = {
                                "event": "scanner_signal_changed",
                                "symbol": symbol,
                                "old_signal": old_signal,
                                "new_signal": new_signal,
                                "confidence_score": result.get("confidence_score", 0.50),
                                "xai_reason": result.get("xai_reason", "")
                            }
                            await manager.publish(event)
                            
                            if new_signal in ["BUY", "SELL"]:
                                prop_id = f"prop-{db.query(ProposalModel).count() + 1}"
                                qty = int(max(1, int(1000000 * 0.05 / candles[-1]["close"]))) if candles else 10
                                sl = candles[-1]["close"] * 0.98 if candles else 98.0
                                tp = candles[-1]["close"] * 1.05 if candles else 105.0
                                risk_score = result.get("confidence_score", 0.50) * 10.0
                                
                                new_prop = ProposalModel(
                                    id=prop_id,
                                    symbol=symbol,
                                    signal=new_signal,
                                    qty=qty,
                                    SL=sl,
                                    TP=tp,
                                    status="pending",
                                    XAIReason=result.get("xai_reason", "Auto-generated signal"),
                                    risk_score=risk_score
                                )
                                db.add(new_prop)
                                db.commit()
                                db.refresh(new_prop)
                                
                                await manager.publish({
                                    "event": "proposal_created",
                                    "id": new_prop.id,
                                    "symbol": new_prop.symbol,
                                    "signal": new_prop.signal,
                                    "qty": new_prop.qty,
                                    "status": new_prop.status
                                })
                                
                                # Autopilot handling
                                state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
                                mode = state.value if state else "copilot"
                                
                                if mode == "autopilot":
                                    portfolio_value = 1000000
                                    buying_power = 0.0
                                    try:
                                        acc_info = alpaca_executor.get_account_info()
                                        portfolio_value = acc_info.get("portfolio_value", 1000000)
                                        buying_power = acc_info.get("buying_power", 0.0)
                                    except Exception:
                                        pass
                                        
                                    trade_value = qty * candles[-1]["close"] if candles else qty * 100.0
                                    trade_pct = (trade_value / portfolio_value) * 100.0
                                    
                                    guardrail_violations = []
                                    if risk_score > 7.0:
                                        guardrail_violations.append(f"Risk score {risk_score:.1f}/10 exceeds maximum allowed 7.0/10.")
                                    if trade_pct > 5.0:
                                        guardrail_violations.append(f"Trade value {trade_pct:.1f}% exceeds 5.0% per-trade guardrail.")
                                    if new_signal.upper() == "BUY" and trade_value > buying_power:
                                        guardrail_violations.append(f"Trade cost ${trade_value:,.2f} exceeds available buying power of ${buying_power:,.2f}.")
                                        
                                    if guardrail_violations:
                                        new_prop.status = "rejected"
                                        db.commit()
                                        
                                        log_id = f"log-{db.query(AuditLogModel).count() + 1}"
                                        db.add(AuditLogModel(
                                            id=log_id,
                                            timestamp=datetime.now(timezone.utc).isoformat(),
                                            symbol=symbol,
                                            action_type="GUARDRAIL_BLOCKED",
                                            qty=qty,
                                            price=candles[-1]["close"] if candles else 100.0,
                                            status="FAILED",
                                            user="autopilot@kerdostat.com"
                                        ))
                                        db.commit()
                                    else:
                                        try:
                                            executor = select_executor_by_symbol(symbol)
                                            executor.submit_order(
                                                symbol=symbol,
                                                qty=qty,
                                                side=new_signal.lower()
                                            )
                                            new_prop.status = "executed"
                                            db.commit()
                                            
                                            log_id = f"log-{db.query(AuditLogModel).count() + 1}"
                                            db.add(AuditLogModel(
                                                id=log_id,
                                                timestamp=datetime.now(timezone.utc).isoformat(),
                                                symbol=symbol,
                                                action_type="AUTO_EXECUTED",
                                                qty=qty,
                                                price=candles[-1]["close"] if candles else 100.0,
                                                status="SUCCESS",
                                                user="autopilot@kerdostat.com"
                                            ))
                                            db.commit()
                                        except Exception as e:
                                            logger.error(f"Autopilot background scanner order failure: {e}")
                    except Exception as ex:
                        logger.error(f"Error scanning symbol {symbol}: {ex}")
            finally:
                db.close()
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Background scanner task cancelled.")
    except Exception as ex:
        logger.error(f"Background scanner task crashed: {ex}")
