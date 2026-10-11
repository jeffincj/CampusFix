// Complaint table with filters, search, paging and a side panel for updates.
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { CATEGORIES, STATUSES, URGENCIES, categoryLabel, formatDate } from "../constants.js";
import { StatusBadge, UrgencyBadge } from "../components/Badges.jsx";
import ComplaintPanel from "../components/ComplaintPanel.jsx";

const EMPTY_FILTERS = { q: "", status: "", category: "", urgency: "", needs_review: "", ordering: "-created_at" };

export default function Complaints() {
  const { user } = useAuth();
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [search, setSearch] = useState(""); // typed text; copied to filters.q after a pause
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  // Wait 300 ms after typing stops before searching (fewer requests).
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => ({ ...f, q: search })), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Go back to page 1 whenever a filter changes.
  useEffect(() => setPage(1), [filters]);

  useEffect(() => {
    const params = new URLSearchParams({ page });
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    setLoading(true);
    api(`/complaints/?${params}`)
      .then((result) => {
        setData(result);
        setError("");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters, page]);

  function setFilter(key, value) {
    setFilters({ ...filters, [key]: value });
  }

  // After an update in the panel, refresh that row without reloading the table.
  function onSaved(updated) {
    setData((d) => ({ ...d, results: d.results.map((c) => (c.id === updated.id ? updated : c)) }));
  }

  const pages = data ? Math.max(1, Math.ceil(data.count / 20)) : 1;

  return (
    <div className={selected ? "with-panel" : ""}>
      <div className="page-head">
        <h1>{user.role === "admin" ? "All complaints" : `${user.department_name || "Department"} complaints`}</h1>
        {data && <span className="muted">{data.count} found</span>}
      </div>

      {/* Filters: one row above the table */}
      <div className="filters">
        <input type="search" placeholder="Search title, description, location" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={filters.status} onChange={(e) => setFilter("status", e.target.value)} aria-label="Status">
          <option value="">All statuses</option>
          {Object.entries(STATUSES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {user.role === "admin" && (
          <select value={filters.category} onChange={(e) => setFilter("category", e.target.value)} aria-label="Category">
            <option value="">All categories</option>
            {Object.entries(CATEGORIES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        )}
        <select value={filters.urgency} onChange={(e) => setFilter("urgency", e.target.value)} aria-label="Urgency">
          <option value="">All urgencies</option>
          {Object.entries(URGENCIES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={filters.ordering} onChange={(e) => setFilter("ordering", e.target.value)} aria-label="Sort">
          <option value="-created_at">Newest first</option>
          <option value="created_at">Oldest first</option>
          <option value="-duplicate_count">Most duplicates</option>
        </select>
        <label className="check">
          <input type="checkbox" checked={filters.needs_review === "true"} onChange={(e) => setFilter("needs_review", e.target.checked ? "true" : "")} />
          Needs review
        </label>
        {JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS) && (
          <button className="link" onClick={() => { setFilters(EMPTY_FILTERS); setSearch(""); }}>Clear</button>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className={`card table-card ${loading ? "loading" : ""}`}>
        <table className="table">
          <thead>
            <tr>
              <th>#</th><th>Complaint</th><th>Category</th><th>Urgency</th><th>Block</th><th>Status</th><th className="num">Dup.</th><th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((c) => (
              <tr key={c.id} className={selected === c.id ? "selected" : ""} onClick={() => setSelected(c.id)} tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setSelected(c.id)}>
                <td className="num">{c.id}</td>
                <td>
                  <div className="title">{c.title} {c.needs_review && <span className="badge review" title="LLM and classifier disagree">⚠ review</span>}</div>
                  {c.summary && <div className="muted small">{c.summary}</div>}
                </td>
                <td>{categoryLabel(c.category)}</td>
                <td><UrgencyBadge urgency={c.urgency} /></td>
                <td>{c.block || "—"}</td>
                <td><StatusBadge status={c.status} /></td>
                <td className="num">{c.duplicate_count || ""}</td>
                <td className="small">{formatDate(c.created_at)}</td>
              </tr>
            ))}
            {data && data.results.length === 0 && (
              <tr><td colSpan={8} className="muted">No complaints match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="pager">
          <button className="button secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button>
          <span>Page {page} of {pages}</span>
          <button className="button secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next →</button>
        </div>
      )}

      {selected && <ComplaintPanel id={selected} onClose={() => setSelected(null)} onSaved={onSaved} />}
    </div>
  );
}
