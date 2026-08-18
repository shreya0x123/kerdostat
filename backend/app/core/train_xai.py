import os
import numpy as np
from sklearn.linear_model import LogisticRegression
import joblib

def generate_synthetic_data(num_samples=1000):
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Generate relative, scale-invariant features
    # 1. RSI: bound between 0 and 100
    rsi = np.random.uniform(10, 90, num_samples)
    
    # 2. MACD histogram: centered around 0
    macd_hist = np.random.normal(0, 2.0, num_samples)
    
    # 3. MACD line & signal
    macd_line = np.random.normal(0, 3.0, num_samples)
    macd_sig = macd_line - (macd_hist * 0.5)
    
    # 4. Close vs EMA deviation percent
    close_minus_ema = np.random.normal(0, 5.0, num_samples)
    
    # 5. Bollinger Bands position (percent B): close relative to upper/lower bands (normally 0 to 1)
    bb_percent = np.random.normal(0.5, 0.25, num_samples)
    bb_percent = np.clip(bb_percent, 0.0, 1.0)
    
    X = np.column_stack((rsi, macd_line, macd_sig, macd_hist, close_minus_ema, bb_percent))
    
    # Calculate probability log-odds logic to make synthetic signals meaningful
    # BUY success probability is higher with low RSI and positive MACD histogram
    # SELL success probability is higher with high RSI and negative MACD histogram
    # Standard log-odds model:
    z = -0.04 * (rsi - 50) + 0.3 * macd_hist + 0.1 * close_minus_ema + 0.5 * (bb_percent - 0.5)
    prob = 1.0 / (1.0 + np.exp(-z))
    y = (prob > np.random.uniform(0.0, 1.0, num_samples)).astype(int)
    
    return X, y

def train_and_save():
    print("Generating synthetic technical indicator dataset...")
    X, y = generate_synthetic_data()
    
    print("Fitting Logistic Regression model...")
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    
    # Determine save path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "model.pkl")
    
    print(f"Saving trained model artifact to {model_path}...")
    joblib.dump(model, model_path)
    print("XAI Model training and serialization complete.")

if __name__ == "__main__":
    train_and_save()
