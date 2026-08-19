const ENV_BASE = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = ENV_BASE
  ? (ENV_BASE.endsWith("/") ? ENV_BASE.slice(0, -1) : ENV_BASE)
  : (window.location.port === "80" ? "/api" : "http://localhost:8000");

const getToken = () => localStorage.getItem("kerdostat_token");
const setToken = (t) => t && localStorage.setItem("kerdostat_token", t);
const removeToken = () => localStorage.removeItem("kerdostat_token");

const getAuthHeaders = () => {
  const t = getToken();
  return t ? { "Authorization": `Bearer ${t}` } : {};
};

export async function fetchProposals() {
  const response = await fetch(`${BASE_URL}/trade/proposals`, {
    headers: { ...getAuthHeaders() },
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
      ...getAuthHeaders(),
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

  const data = await response.json();
  if (data.token || data.access_token) {
    setToken(data.token || data.access_token);
  }
  return data;
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

  const data = await response.json();
  if (data.token || data.access_token) {
    setToken(data.token || data.access_token);
  }
  return data;
}

export async function logoutUser() {
  removeToken();
  const response = await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });

  return response.json().catch(() => ({ status: "success" }));
}

export async function fetchMe() {
  const response = await fetch(`${BASE_URL}/auth/me`, {
    method: "GET",
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Session invalid or expired.");
  }

  return response.json();
}

export async function fetchOHLCV(range = "1D", symbol = "QUANT") {
  const response = await fetch(`${BASE_URL}/market/ohlcv?range=${range}&symbol=${symbol}`, {
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch OHLCV: ${response.statusText}`);
  }
  return response.json();
}

export async function searchAssets(query) {
  const response = await fetch(`${BASE_URL}/market/search?q=${encodeURIComponent(query)}`, {
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to search assets: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchSignal(range = "1D", symbol = "QUANT") {
  const response = await fetch(`${BASE_URL}/market/signal?range=${range}&symbol=${symbol}`, {
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch signal: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchAuditLogs() {
  const response = await fetch(`${BASE_URL}/trade/audit-logs`, {
    headers: { ...getAuthHeaders() },
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch mode: ${response.statusText}`);
  }
  return response.json();
}

export async function updateMode(mode) {
  const response = await fetch(`${BASE_URL}/user/mode`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
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
    headers: { ...getAuthHeaders() },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch account details: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchPositions() {
  const response = await fetch(`${BASE_URL}/trade/positions`, {
    headers: { ...getAuthHeaders() },
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

