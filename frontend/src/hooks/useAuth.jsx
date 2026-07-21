/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchMe, loginUser, registerUser, logoutUser, fetchMode, updateMode, fetchAccountDetails } from "@/services/apiService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [state, setState] = useState({
    user: null,
    isAuthenticated: false,
    isBrokerConnected: false,
    systemMode: "copilot",
    loading: true,
  });

  // Verify active JWT cookie session and system mode on load
  useEffect(() => {
    async function verifySession() {
      let user = null;
      let authenticated = false;
      let brokerConnected = false;
      try {
        user = await fetchMe();
        authenticated = true;
        
        try {
          const acc = await fetchAccountDetails();
          brokerConnected = acc && !acc.error;
        } catch (err) {
          console.error("Broker connection check failed on session verify:", err);
        }
      } catch {
        // Ignore auth check failures
      }

      let mode = "copilot";
      try {
        const modeData = await fetchMode();
        mode = modeData.mode;
      } catch (err) {
        console.error("Failed to fetch system mode on load:", err);
      }

      console.log("[useAuth] verifySession setting state:", {
        user,
        isAuthenticated: authenticated,
        isBrokerConnected: brokerConnected,
        systemMode: mode,
        loading: false,
      });
      setState({
        user,
        isAuthenticated: authenticated,
        isBrokerConnected: brokerConnected,
        systemMode: mode,
        loading: false,
      });
    }
    verifySession();
  }, []);

  const value = useMemo(
    () => ({
      user: state.user,
      isAuthenticated: state.isAuthenticated,
      isBrokerConnected: state.isBrokerConnected,
      systemMode: state.systemMode,
      loading: state.loading,
      signIn: async (email, password) => {
        const user = await loginUser(email, password);
        let brokerConnected = false;
        try {
          const acc = await fetchAccountDetails();
          brokerConnected = acc && !acc.error;
        } catch {}
        setState((prev) => ({
          ...prev,
          user,
          isAuthenticated: true,
          isBrokerConnected: brokerConnected,
        }));
        return user;
      },
      signUp: async (name, email, password) => {
        const user = await registerUser(name, email, password);
        let brokerConnected = false;
        try {
          const acc = await fetchAccountDetails();
          brokerConnected = acc && !acc.error;
        } catch {}
        setState((prev) => ({
          ...prev,
          user,
          isAuthenticated: true,
          isBrokerConnected: brokerConnected,
        }));
        return user;
      },
      signOut: async () => {
        try {
          await logoutUser();
        } catch (err) {
          console.error("Logout error on server:", err);
        } finally {
          setState({
            user: null,
            isAuthenticated: false,
            isBrokerConnected: false,
            systemMode: "copilot",
            loading: false,
          });
          localStorage.removeItem("kerdostat-broker-connected");
        }
      },
      connectBroker: () => {
        setState((prev) => ({ ...prev, isBrokerConnected: true }));
        localStorage.setItem("kerdostat-broker-connected", "true");
      },
      disconnectBroker: () => {
        setState((prev) => ({ ...prev, isBrokerConnected: false }));
        localStorage.setItem("kerdostat-broker-connected", "false");
      },
      toggleSystemMode: async () => {
        const nextMode = state.systemMode === "copilot" ? "autopilot" : "copilot";
        console.log("[useAuth] toggleSystemMode called. Next mode:", nextMode);
        try {
          const res = await updateMode(nextMode);
          console.log("[useAuth] updateMode response received:", res);
          setState((prev) => ({ ...prev, systemMode: res.mode }));
        } catch (err) {
          console.error("[useAuth] Failed to update system mode:", err);
        }
      },
    }),
    [state.user, state.isAuthenticated, state.isBrokerConnected, state.systemMode, state.loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
