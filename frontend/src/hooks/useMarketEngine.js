import { useEffect, useRef, useState } from "react";
import { fetchOHLCV } from "@/services/apiService";

const XAI_MESSAGES = [
  "Mean-reversion trigger detected on 5m canvas.",
  "Order book imbalance leaning bearish, executing micro-hedge.",
  "Volatility compression observed ahead of scheduled event.",
  "Liquidity sweep detected, adjusting risk exposure.",
  "Alpha signal confirms momentum continuation on QUANT.",
  "Pair correlation weakening; switching to defensive bias.",
  "Execution algorithim recalibrated for limit order slicing.",
  "Stress test flagged elevated skew, reducing position size.",
];

const randomInt = (min, max) =>
  Math.floor(Math.random() * (max - min + 1)) + min;
const randomItem = (items) => items[randomInt(0, items.length - 1)];

export default function useMarketEngine(symbol = "QUANT") {
  const [candleData, setCandleData] = useState([]);
  const [xaiLogs, setXaiLogs] = useState([
    `[00:00:00] Market feed initialized for ${symbol}.`,
    "[00:00:02] Quality checks nominal, running live algo loop.",
  ]);
  const tickRef = useRef(0);

  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        const data = await fetchOHLCV("1D", symbol);
        if (active) {
          if (data && data.length > 0) {
            setCandleData(data);
          } else {
            setCandleData([]);
          }
        }
      } catch (err) {
        console.error("Failed to fetch live market data inside useMarketEngine", err);
        if (active) {
          setCandleData([]);
        }
      }
    }

    setCandleData([]);
    loadData();
    const intervalId = window.setInterval(loadData, 5000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [symbol]);

  useEffect(() => {
    const logIntervalId = window.setInterval(() => {
      tickRef.current += 1;
      if (tickRef.current % randomInt(3, 6) === 0) {
        setXaiLogs((previousLogs) => {
          const nextLog = `[${new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}] ${randomItem(XAI_MESSAGES).replace("QUANT", symbol)}`;
          const nextLogs = [...previousLogs, nextLog];
          return nextLogs.slice(-12);
        });
      }
    }, 2000);

    return () => {
      window.clearInterval(logIntervalId);
    };
  }, [symbol]);

  const currentPrice = candleData[candleData.length - 1]?.close ?? 0;

  return { candleData, currentPrice, xaiLogs };
}
