// Side panel with one complaint's details, AI results, history, and the update form.
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ALLOWED_TRANSITIONS, CATEGORIES, STATUSES, URGENCIES, categoryLabel, formatDate } from "../constants.js";
import { StatusBadge, UrgencyBadge } from "./Badges.jsx";

export default function ComplaintPanel({ id, onClose, onSaved }) {
  const { user } = useAuth();
  const [complaint, setComplaint] = useState(null);
  const [form, setForm] = useState({ status: "", note: "", urgency: "", category: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setComplaint(null);
    api(`/complaints/${id}/`)
      .then((data) => {
        setComplaint(data);
        setForm({ status: "", note: "", urgency: data.urgency, category: data.category });
      })
      .catch((err) => setError(err.message));
  }, [id]);

  async function save(event) {
    event.preventDefault();
    // Only send fields that changed.
    const changes = {};
    if (form.status) changes.status = form.status;
    if (form.status && form.note.trim()) changes.note = form.note.trim();
    if (form.urgency !== complaint.urgency) changes.urgency = form.urgency;
    if (user.role === "admin" && form.category !== complaint.category) changes.category = form.category;
    if (Object.keys(changes).length === 0) {
      setError("Nothing to save.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await api(`/complaints/${id}/`, { method: "PATCH", body: changes });
      setComplaint(updated);
      setForm({ status: "", note: "", urgency: updated.urgency, category: updated.category });
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function markReviewed() {
    try {
      const updated = await api(`/complaints/${id}/`, { method: "PATCH", body: { needs_review: false } });
      setComplaint(updated);
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!complaint) {
    return (
      <aside className="panel">
        <button className="link close" onClick={onClose}>Close ✕</button>
        {error ? <div className="alert error">{error}</div> : <p className="muted">Loading…</p>}
      </aside>
    );
  }

  const nextStatuses = ALLOWED_TRANSITIONS[complaint.status] || [];

  return (
    <aside className="panel" aria-label={`Complaint ${complaint.id}`}>
      <button className="link close" onClick={onClose}>Close ✕</button>
      <h2>#{complaint.id} · {complaint.title}</h2>
      <div className="row gap">
        <StatusBadge status={complaint.status} />
        <UrgencyBadge urgency={complaint.urgency} />
        {complaint.needs_review && <span className="badge review">⚠ Needs review</span>}
      </div>

      <p className="description">{complaint.description}</p>
      <dl className="details">
        <dt>Category</dt><dd>{categoryLabel(complaint.category)}</dd>
        <dt>Department</dt><dd>{complaint.department_name || "—"}</dd>
        <dt>Location</dt><dd>{complaint.location || "—"} {complaint.block && `(${complaint.block})`}</dd>
        <dt>Student</dt><dd>{complaint.student}</dd>
        <dt>Submitted</dt><dd>{formatDate(complaint.created_at)}</dd>
        <dt>Predicted fix</dt><dd>{complaint.predicted_days ? `${complaint.predicted_days} days` : "—"}</dd>
        <dt>Duplicates</dt>
        <dd>
          {complaint.duplicate_count} merged
          {complaint.duplicate_of && ` · duplicate of #${complaint.duplicate_of.id} (${Math.round(complaint.duplicate_of.similarity * 100)}% similar)`}
        </dd>
      </dl>

      <h3>AI</h3>
      <dl className="details">
        <dt>Summary</dt><dd>{complaint.summary || "—"}</dd>
        <dt>Language</dt><dd>{complaint.language || "—"}</dd>
        <dt>Decided by</dt><dd>{complaint.ai_source || "—"}</dd>
        <dt>LLM</dt><dd>{complaint.llm_category ? categoryLabel(complaint.llm_category) : "—"}</dd>
        <dt>Classifier</dt>
        <dd>
          {complaint.ml_category ? categoryLabel(complaint.ml_category) : "—"}
          {complaint.ml_confidence != null && ` (${Math.round(complaint.ml_confidence * 100)}%)`}
        </dd>
      </dl>
      {complaint.needs_review && user.role === "admin" && (
        <div className="alert warning">
          The LLM and the classifier disagree. Check the category, then{" "}
          <button className="link" onClick={markReviewed}>mark as reviewed</button>.
        </div>
      )}

      <h3>Update</h3>
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={save} className="stack">
        <label>
          New status
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} disabled={!nextStatuses.length}>
            <option value="">{nextStatuses.length ? "Keep current status" : "No further changes"}</option>
            {nextStatuses.map((s) => <option key={s} value={s}>{STATUSES[s]}</option>)}
          </select>
        </label>
        {form.status && (
          <label>
            Note (shown in the history)
            <input value={form.note} maxLength={300} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </label>
        )}
        <label>
          Urgency
          <select value={form.urgency} onChange={(e) => setForm({ ...form, urgency: e.target.value })}>
            {Object.entries(URGENCIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        {user.role === "admin" && (
          <label>
            Category (re-routes to that department)
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {Object.entries(CATEGORIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        )}
        <button className="button" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button>
      </form>

      <h3>History</h3>
      <ol className="timeline">
        {complaint.history.map((h, i) => (
          <li key={i}>
            <StatusBadge status={h.new_status} /> <span className="muted small">{formatDate(h.created_at)}{h.changed_by && ` · ${h.changed_by}`}</span>
            {h.note && <div>{h.note}</div>}
          </li>
        ))}
      </ol>
    </aside>
  );
}
