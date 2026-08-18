import React, { createContext, useContext, useState, useEffect } from "react";
import { connectWebSocket } from "@/services/apiService";

const MarketStoreContext = createContext(null);

export function MarketStoreProvider({ children }) {
  const [livePrices, setLivePrices] = useState({});
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    let ws;
    try {
      ws = connectWebSocket((event) => {
        if (event.event === "connected") {
          setWsConnected(true);
        } else if (event.event === "scanner_signal_changed") {
          setActiveAlerts((prev) => [event, ...prev.slice(0, 9)]);
        }
      });
    } catch (err) {
      console.warn("MarketStore WebSocket connection skipped:", err);
    }

    return () => {
      if (ws && typeof ws.close === "function") {
        ws.close();
      }
    };
  }, []);

  const updatePrice = (symbol, price) => {
    setLivePrices((prev) => ({ ...prev, [symbol]: price }));
  };

  return (
    <MarketStoreContext.Provider value={{ livePrices, activeAlerts, wsConnected, updatePrice }}>
      {children}
    </MarketStoreContext.Provider>
  );
}

export function useMarketStore() {
  const context = useContext(MarketStoreContext);
  return context || { livePrices: {}, activeAlerts: [], wsConnected: false };
}
