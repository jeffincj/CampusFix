// Routes + page layout. Which pages a user sees depends on their role.
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Login from "./pages/Login.jsx";
import Complaints from "./pages/Complaints.jsx";
import Charts from "./pages/Charts.jsx";
import Hotspots from "./pages/Hotspots.jsx";
import Spikes from "./pages/Spikes.jsx";
import Chat from "./pages/Chat.jsx";
import Metrics from "./pages/Metrics.jsx";
import Documents from "./pages/Documents.jsx";

// path, label, page component, roles allowed
const PAGES = [
  ["/complaints", "Complaints", Complaints, ["staff", "admin"]],
  ["/charts", "Charts", Charts, ["staff", "admin"]],
  ["/hotspots", "Hotspots", Hotspots, ["staff", "admin"]],
  ["/spikes", "Spike alerts", Spikes, ["staff", "admin"]],
  ["/chat", "Assistant", Chat, ["staff", "admin"]],
  ["/metrics", "AI metrics", Metrics, ["admin"]],
  ["/documents", "Rule documents", Documents, ["admin"]],
];

export default function App() {
  const { user, logout } = useAuth();

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
      <header className="topbar">
        <span className="brand">CampusFix</span>
        <nav className="nav">
          {myPages.map(([path, label]) => (
            <NavLink key={path} to={path}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="who">
          <span>
            {user.username} · {user.role}
            {user.department_name ? ` · ${user.department_name}` : ""}
          </span>
          <button className="link" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
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
