// Login state for the whole app (React context).
import { createContext, useContext, useEffect, useState } from "react";
import { api, clearSession, loadUser, saveSession } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadUser);

  // api.js fires this event when the refresh token has expired.
  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("campusfix:logout", onLogout);
    return () => window.removeEventListener("campusfix:logout", onLogout);
  }, []);

  async function login(username, password) {
    const data = await api("/auth/login/", { method: "POST", body: { username, password } });
    if (data.user.role === "student") {
      // Students have their own website; this dashboard is for officials only.
      throw new Error("This dashboard is for staff and admins. Students, please use the student website.");
    }
    saveSession(data);
    setUser(data.user);
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
