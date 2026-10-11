// Hotspots: places with many complaints of the same category (DBSCAN clusters).
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { categoryLabel, formatDate } from "../constants.js";
import CampusMap from "../components/CampusMap.jsx";

export default function Hotspots() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null); // hotspot highlighted on both the map and the list

  useEffect(() => {
    api(`/hotspots/?days=${days}`).then(setData).catch((err) => setError(err.message));
  }, [days]);

  return (
    <div>
      <div className="page-head">
        <h1>Hotspots</h1>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>
      <p className="muted">
        Groups of at least 4 complaints of the same category within about 70 m of each other, found with DBSCAN.
        Isolated complaints are left out.
      </p>
      {error && <div className="alert error">{error}</div>}
      {data && data.hotspots.length === 0 && <p className="muted">No hotspots in this period.</p>}

      {data && data.hotspots.length > 0 && (
        <section className="card">
          <CampusMap campus={data.campus} hotspots={data.hotspots} active={active} onActivate={setActive} />
        </section>
      )}

      <div className="list">
        {data?.hotspots.map((h, i) => (
          <article key={i} className={`card hotspot ${active === i ? "active" : ""}`}
                   onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)}>
            <div className="hotspot-count">
              <strong>{h.count}</strong>
              <span className="muted small">complaints</span>
            </div>
            <div className="grow">
              <h3>{categoryLabel(h.category)} · {h.blocks.join(", ")}</h3>
              <p className="small">
                {h.places.map((p) => `${p.place} (${p.count})`).join(" · ")}
              </p>
              <p className="muted small">
                {h.open_count} still open · latest {formatDate(h.latest)} · complaint ids {h.complaint_ids.slice(0, 8).join(", ")}
                {h.complaint_ids.length > 8 && "…"}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
