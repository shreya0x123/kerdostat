import logging
import sys
import os

def setup_logger(name: str = "kerdostat") -> logging.Logger:
    """
    Configures and returns a centralized, structured logger.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler in logs directory if available
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
        if os.path.exists(logs_dir):
            try:
                file_handler = logging.FileHandler(os.path.join(logs_dir, "kerdostat.log"))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception:
                pass
                
    return logger

logger = setup_logger("kerdostat-backend")
