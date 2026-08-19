/* eslint-disable react-hooks/refs, react-hooks/set-state-in-effect */
import { useEffect, useRef, useState, useCallback } from "react";

const getDefaultWsUrl = () => {
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase) {
    const wsProto = envBase.startsWith("https:") ? "wss:" : "ws:";
    const cleanHost = envBase.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return `${wsProto}//${cleanHost}/ws`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  if (window.location.port === "80") {
    return `${protocol}//${window.location.host}/ws`;
  }
  return "ws://localhost:8000/ws";
};

export default function useWebSocket(url = getDefaultWsUrl()) {
  const [connected, setConnected] = useState(false);
  const [latestMessage, setLatestMessage] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef(null);

  const connect = useCallback(() => {
    // Clear any pending reconnects
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    try {
      console.log(`[WebSocket] Connecting to ${url}...`);
      const socket = new WebSocket(url);

      socket.onopen = () => {
        console.log("[WebSocket] Connection established.");
        setConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.type === "ping" || parsed.event === "heartbeat") {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: "pong", timestamp: Date.now() }));
            }
            return;
          }
          setLatestMessage(parsed);
        } catch {
          setLatestMessage(event.data);
        }
      };

      socket.onclose = (event) => {
        console.log(`[WebSocket] Connection closed (code: ${event.code}).`);
        setConnected(false);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff (max 30s)
        const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptsRef.current));
        reconnectAttemptsRef.current += 1;

        console.log(`[WebSocket] Attempting reconnect in ${(delay / 1000).toFixed(1)}s...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          if (connectRef.current) {
            connectRef.current();
          }
        }, delay);
      };

      socket.onerror = (error) => {
        console.error("[WebSocket] Error caught:", error);
        socket.close(); // Triggers onclose to run reconnect logic
      };

      wsRef.current = socket;
    } catch (err) {
      console.error("[WebSocket] Connection error:", err);
      setConnected(false);
    }
  }, [url]);

  // Keep connectRef fresh so connect() can reference itself safely
  connectRef.current = connect;

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        // Remove close listener to prevent reconnect loops on manual unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const data = typeof msg === "object" ? JSON.stringify(msg) : msg;
      wsRef.current.send(data);
    } else {
      console.warn("[WebSocket] Cannot send message, socket is not open.");
    }
  }, []);

  return { connected, latestMessage, sendMessage };
}
