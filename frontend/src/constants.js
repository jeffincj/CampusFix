// Labels and workflow rules shared by the pages (mirrors the Django backend).

export const CATEGORIES = {
  HOSTEL: "Hostel",
  MESS: "Mess & Food",
  IT: "Wi-Fi & IT",
  LAB: "Labs & Academics",
  TRANSPORT: "Transport",
  MAINTENANCE: "Electrical & Plumbing",
  SANITATION: "Cleanliness & Sanitation",
  SECURITY: "Safety & Security",
};

export const STATUSES = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
  rejected: "Rejected",
};

export const URGENCIES = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };

// Same rules as complaints/services.py (the server checks them again).
export const ALLOWED_TRANSITIONS = {
  open: ["in_progress", "resolved", "rejected"],
  in_progress: ["resolved", "open"],
  resolved: ["closed", "in_progress"],
  closed: [],
  rejected: [],
};

export function categoryLabel(code) {
  return CATEGORIES[code] || code || "Unknown";
}

export function formatDate(iso) {
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
