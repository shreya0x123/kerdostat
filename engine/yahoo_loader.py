import yfinance as yf


def fetch_ohlcv(symbol: str, period: str = "1mo"):
    data = yf.download(
        symbol,
        period=period,
        auto_adjust=True
    )

    return data


if __name__ == "__main__":
    df = fetch_ohlcv("AAPL")

    print(df.head())