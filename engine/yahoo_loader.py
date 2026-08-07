import yfinance as yf


def fetch_ohlcv(symbol="AAPL", period="1mo"):
    df = yf.download(
        symbol,
        period=period,
        auto_adjust=True
    )

    # flatten multi-index
    if isinstance(df.columns, type(df.columns)):
        if len(df.columns.names) > 1:
            df.columns = df.columns.get_level_values(0)

    return df


if __name__ == "__main__":
    df = fetch_ohlcv()

    print(df.columns)
    print()
    print(df.tail())