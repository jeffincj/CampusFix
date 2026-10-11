// Routes + page layout. Which pages a user sees depends on their role.
import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Icon from "./components/Icon.jsx";
import { useAuth } from "./auth.jsx";
import Login from "./pages/Login.jsx";
import Complaints from "./pages/Complaints.jsx";
import Charts from "./pages/Charts.jsx";
import Hotspots from "./pages/Hotspots.jsx";
import Spikes from "./pages/Spikes.jsx";
import Chat from "./pages/Chat.jsx";
import Metrics from "./pages/Metrics.jsx";
import Documents from "./pages/Documents.jsx";

// path, label, page component, roles allowed, icon
const PAGES = [
  ["/complaints", "Complaints", Complaints, ["staff", "admin"], "list"],
  ["/charts", "Charts", Charts, ["staff", "admin"], "chart"],
  ["/hotspots", "Hotspots", Hotspots, ["staff", "admin"], "pin"],
  ["/spikes", "Spike alerts", Spikes, ["staff", "admin"], "bolt"],
  ["/chat", "Assistant", Chat, ["staff", "admin"], "chat"],
  ["/metrics", "AI metrics", Metrics, ["admin"], "gauge"],
  ["/documents", "Rule documents", Documents, ["admin"], "file"],
];

// Light/dark theme: follows the system until the user picks one (saved in localStorage).
function useTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("campusfix-theme");
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (theme) document.documentElement.setAttribute("data-theme", theme);
    try {
      if (theme) localStorage.setItem("campusfix-theme", theme);
    } catch {
      /* private mode: ignore */
    }
  }, [theme]);
  const isDark = theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  return [isDark, () => setTheme(isDark ? "light" : "dark")];
}

export default function App() {
  const { user, logout } = useAuth();
  const [isDark, toggleTheme] = useTheme();

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  const myPages = PAGES.filter(([, , , roles]) => roles.includes(user.role));

  return (
    <div className="layout">
      {/* Sidebar navigation (becomes a top bar on small screens) */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><Icon name="logo" /></span> CampusFix
        </div>
        <nav className="nav">
          {myPages.map(([path, label, , , icon]) => (
            <NavLink key={path} to={path}>
              <Icon name={icon} /> <span>{label}</span>
            </NavLink>
          ))}
          <a href="/" className="nav-external">
            <Icon name="external" /> <span>Student site</span>
          </a>
        </nav>
        <div className="sidebar-foot">
          <div className="user-card">
            <span className="avatar">{user.username[0]}</span>
            <div>
              <strong>{user.username}</strong>
              <div className="muted small">{user.role}{user.department_name ? ` · ${user.department_name}` : ""}</div>
            </div>
          </div>
          <div className="row gap">
            <button className="icon-button" onClick={toggleTheme} title="Light / dark mode" aria-label="Light / dark mode">
              <Icon name={isDark ? "sun" : "moon"} />
            </button>
            <button className="icon-button" onClick={logout} title="Log out" aria-label="Log out">
              <Icon name="logout" />
            </button>
          </div>
        </div>
      </aside>
      <main className="content">
        <Routes>
          {myPages.map(([path, , Page]) => (
            <Route key={path} path={path} element={<Page />} />
          ))}
          <Route path="*" element={<Navigate to="/complaints" replace />} />
        </Routes>
      </main>
    </div>
  );
}
