import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.core.alpaca_executor import AlpacaExecutor

def main():
    print("Testing Alpaca broker connection...")
    executor = AlpacaExecutor()
    acc = executor.get_account_info()
    print("Account Info:", acc)
    pos = executor.get_positions()
    print(f"Active Positions ({len(pos)}):", pos)

if __name__ == "__main__":
    main()
