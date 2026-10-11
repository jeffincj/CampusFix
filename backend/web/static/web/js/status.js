/*
 * Live status refresh.
 * Every 15 seconds, ask the server for the current status of the complaints
 * shown on this page, and update their badges without reloading the page.
 */

const REFRESH_MS = 15000;

// All badges on the page, e.g. <span data-status-for="7">Open</span>
function findBadges() {
  return Array.from(document.querySelectorAll("[data-status-for]"));
}

async function refreshStatuses() {
  const url = document.body.dataset.statusUrl;
  const badges = findBadges();
  if (!url || badges.length === 0) return;

  // Collect the unique complaint ids shown on the page.
  const ids = [...new Set(badges.map((b) => b.dataset.statusFor))];

  try {
    const response = await fetch(`${url}?ids=${ids.join(",")}`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin", // send the session cookie
    });
    if (!response.ok) return; // e.g. logged out: just stop updating quietly
    const data = await response.json();

    for (const item of data.complaints) {
      for (const badge of badges.filter((b) => b.dataset.statusFor === String(item.id))) {
        if (badge.textContent !== item.status_display) {
          // Status changed: update text + colour and flash the badge.
          badge.textContent = item.status_display;
          badge.className = `badge status-${item.status} changed`;
        }
      }
    }
  } catch (err) {
    // Network problem: try again on the next tick.
    console.warn("Status refresh failed:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (findBadges().length === 0) return;
  setInterval(() => {
    // Don't poll while the tab is hidden; saves server work.
    if (!document.hidden) refreshStatuses();
  }, REFRESH_MS);
});
