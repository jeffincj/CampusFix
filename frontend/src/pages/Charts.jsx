// Charts: complaints per category, weekly trend, per block. Admins can download the weekly PDF report.
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { categoryLabel } from "../constants.js";
import { ChartCard, HorizontalBars, StatTile, TrendLine } from "../components/charts.jsx";

function weekLabel(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export default function Charts() {
  const { user } = useAuth();
  const [weeks, setWeeks] = useState(12);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api(`/complaints/stats/?weeks=${weeks}`).then(setStats).catch((err) => setError(err.message));
  }, [weeks]);

  async function downloadReport() {
    setDownloading(true);
    setError("");
    try {
      const response = await api("/reports/weekly/", { raw: true });
      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `campusfix-weekly-report-${new Date().toISOString().slice(0, 10)}.pdf`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  const count = (status) => stats?.by_status.find((s) => s.key === status)?.count ?? 0;
  const byCategory = (stats?.by_category || []).map((r) => ({ label: categoryLabel(r.key), count: r.count }));
  const byBlock = (stats?.by_block || []).slice(0, 12).map((r) => ({ label: r.key, count: r.count }));

  return (
    <div>
      <div className="page-head">
        <h1>Charts</h1>
        <div className="row gap">
          <select value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} aria-label="Weeks">
            <option value={4}>Last 4 weeks</option>
            <option value={8}>Last 8 weeks</option>
            <option value={12}>Last 12 weeks</option>
          </select>
          {user.role === "admin" && (
            <button className="button" onClick={downloadReport} disabled={downloading}>
              {downloading ? "Preparing PDF…" : "Download weekly report (PDF)"}
            </button>
          )}
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}

      {stats && (
        <div className={!stats ? "loading" : ""}>
          <div className="tiles">
            <StatTile label="Total complaints" value={stats.total.toLocaleString()} />
            <StatTile label="Open" value={count("open")} />
            <StatTile label="In progress" value={count("in_progress")} />
            <StatTile label="Resolved or closed" value={count("resolved") + count("closed")} />
          </div>

          <div className="grid-2">
            <ChartCard title="Complaints per category" subtitle="All time" rows={byCategory}
                       columns={[["label", "Category"], ["count", "Complaints"]]}>
              <HorizontalBars data={byCategory} />
            </ChartCard>
            <ChartCard title="Complaints per block" subtitle="Top 12 blocks, all time" rows={byBlock}
                       columns={[["label", "Block"], ["count", "Complaints"]]}>
              <HorizontalBars data={byBlock} />
            </ChartCard>
          </div>

          <ChartCard title="Weekly trend" subtitle={`New complaints per week (week starting Monday), last ${weeks} weeks`}
                     rows={stats.by_week.map((w) => ({ week: weekLabel(w.week), count: w.count }))}
                     columns={[["week", "Week of"], ["count", "Complaints"]]}>
            <TrendLine data={stats.by_week} xKey="week" formatX={weekLabel} />
          </ChartCard>
        </div>
      )}
    </div>
  );
}
