// Small wrapper around fetch() for the Django REST API.
// - adds the JWT access token to every request
// - when the access token has expired (401), gets a new one with the refresh token and retries once
// - turns error responses into JavaScript errors with the server's message

const ACCESS_KEY = "campusfix_access";
const REFRESH_KEY = "campusfix_refresh";
const USER_KEY = "campusfix_user";

export function saveSession({ access, refresh, user }) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function clearSession() {
  [ACCESS_KEY, REFRESH_KEY, USER_KEY].forEach((key) => localStorage.removeItem(key));
}

// Called when the session is gone for good (refresh token expired). The app listens for it.
function sessionExpired() {
  clearSession();
  window.dispatchEvent(new Event("campusfix:logout"));
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const response = await fetch("/api/auth/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return false;
  const data = await response.json();
  localStorage.setItem(ACCESS_KEY, data.access);
  return true;
}

function errorMessage(data, status) {
  if (!data) return `Request failed (${status})`;
  if (typeof data.detail === "string") return data.detail;
  // Field errors: {"status": ["Cannot change ..."]}
  return Object.entries(data)
    .map(([field, errors]) => `${field}: ${[].concat(errors).join(" ")}`)
    .join("; ");
}

/**
 * api("/complaints/?status=open")                      -> GET, returns JSON
 * api("/complaints/7/", { method: "PATCH", body: {...} })
 * api("/documents/", { method: "POST", form: formData }) -> file upload
 * api("/reports/weekly/", { raw: true })               -> returns the Response (for files)
 */
export async function api(path, { method = "GET", body, form, raw = false } = {}, retried = false) {
  const headers = {};
  const token = localStorage.getItem(ACCESS_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });

  if (response.status === 401 && !retried && path !== "/auth/login/") {
    if (await refreshAccessToken()) return api(path, { method, body, form, raw }, true);
    sessionExpired();
    throw new Error("Your session has expired. Please log in again.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(errorMessage(data, response.status));
  }
  if (raw) return response;
  if (response.status === 204) return null;
  return response.json();
}
