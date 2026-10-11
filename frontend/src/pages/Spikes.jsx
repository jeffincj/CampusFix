// Spike alerts: hours with unusually many complaints (Isolation Forest).
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { categoryLabel } from "../constants.js";

function hourLabel(iso) {
  const start = new Date(iso);
  const end = new Date(start.getTime() + 3600 * 1000);
  const day = start.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" });
  const time = (d) => d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  return `${day}, ${time(start)}–${time(end)}`;
}

export default function Spikes() {
  const [days, setDays] = useState(14);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/spikes/?days=${days}`).then(setData).catch((err) => setError(err.message));
  }, [days]);

  return (
    <div>
      <div className="page-head">
        <h1>Spike alerts</h1>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
          <option value={3}>Last 3 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>
      <p className="muted">
        Hours with an unusual number of new complaints (Isolation Forest on complaints per hour, at least 5 in the hour).
        A spike often means one outage hit many students.
      </p>
      {error && <div className="alert error">{error}</div>}
      {data && data.spikes.length === 0 && <p className="status-line good">✓ No spikes in this period.</p>}

      <div className="list">
        {data?.spikes.map((s) => (
          <article key={s.hour} className="card alert-card">
            <div className="status-line warning">⚠ Spike</div>
            <h3>{hourLabel(s.hour)}</h3>
            <p>
              <strong>{s.count}</strong> complaints in one hour (a busy hour usually has {s.typical}).
            </p>
            <p className="small">
              {s.categories.map((c) => `${categoryLabel(c.category)}: ${c.count}`).join(" · ")}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
