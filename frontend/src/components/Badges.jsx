// Small coloured labels. Colour is never the only signal: the text always says the value.
import { STATUSES, URGENCIES } from "../constants.js";

export function StatusBadge({ status }) {
  return <span className={`badge status-${status}`}>{STATUSES[status] || status}</span>;
}

export function UrgencyBadge({ urgency }) {
  const icon = { critical: "▲▲", high: "▲", medium: "•", low: "▽" }[urgency] || "";
  return (
    <span className={`badge urgency-${urgency}`}>
      {icon} {URGENCIES[urgency] || urgency}
    </span>
  );
}
