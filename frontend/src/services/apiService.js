const ENV_BASE = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = ENV_BASE
  ? (ENV_BASE.endsWith("/") ? ENV_BASE.slice(0, -1) : ENV_BASE)
  : (window.location.port === "80" ? "/api" : "http://localhost:8000");

export async function fetchProposals() {
  const response = await fetch(`${BASE_URL}/trade/proposals`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch proposals: ${response.statusText}`);
  }
  return response.json();
}

export async function updateProposalAction(proposalId, action) {
  const response = await fetch(`${BASE_URL}/trade/${proposalId}/action`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action }),
    credentials: "include",
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update proposal action: ${response.statusText}`);
  }
  
  return response.json();
}

// Authentication API Helpers
export async function loginUser(email, password) {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Authentication failed.");
  }

  return response.json();
}

export async function registerUser(name, email, password) {
  const response = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, email, password }),
    credentials: "include",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed.");
  }

  return response.json();
}

export async function logoutUser() {
  const response = await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Logout failed on server.");
  }

  return response.json();
}

export async function fetchMe() {
  const response = await fetch(`${BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Session invalid or expired.");
  }

  return response.json();
}

export async function fetchOHLCV(range = "1D", symbol = "QUANT") {
  const response = await fetch(`${BASE_URL}/market/ohlcv?range=${range}&symbol=${symbol}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch OHLCV: ${response.statusText}`);
  }
  return response.json();
}

export async function searchAssets(query) {
  const response = await fetch(`${BASE_URL}/market/search?q=${encodeURIComponent(query)}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to search assets: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchSignal(range = "1D", symbol = "QUANT") {
  const response = await fetch(`${BASE_URL}/market/signal?range=${range}&symbol=${symbol}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch signal: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchAuditLogs() {
  const response = await fetch(`${BASE_URL}/trade/audit-logs`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch audit logs: ${response.statusText}`);
  }
  return response.json();
}

export async function executeHijack(payload) {
  const response = await fetch(`${BASE_URL}/trade/hijack`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    credentials: "include",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to execute hijack: ${response.statusText}`);
  }
  return response.json();
}

export async function overrideProposal(id, payload) {
  const response = await fetch(`${BASE_URL}/trade/${id}/override`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    credentials: "include",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to execute override: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchMode() {
  const response = await fetch(`${BASE_URL}/trade/mode`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch mode: ${response.statusText}`);
  }
  return response.json();
}

export async function updateMode(mode) {
  const response = await fetch(`${BASE_URL}/trade/mode`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ mode }),
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to update mode: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchAccountDetails() {
  const response = await fetch(`${BASE_URL}/trade/account`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch account details: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchPositions() {
  const response = await fetch(`${BASE_URL}/trade/positions`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch positions: ${response.statusText}`);
  }
  return response.json();
}

export function connectWebSocket(onMessage, url) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = url || ((window.location.port === "80" || window.location.port === "") ? `${protocol}//${window.location.host}/ws` : "ws://localhost:8000/ws");
  try {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      if (onMessage) onMessage({ event: "connected" });
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch {
        if (onMessage) onMessage(event.data);
      }
    };
    ws.onerror = (err) => {
      console.warn("WebSocket error:", err);
    };
    return ws;
  } catch (err) {
    console.warn("Failed to create WebSocket:", err);
    return null;
  }
}

