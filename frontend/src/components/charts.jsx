// Chart building blocks (Recharts), styled with the theme tokens in theme.css.
// Animations are off: charts appear at once and don't jump when filters reload the data.
// Every chart card has a "Table" toggle, so values never depend on colour or hover.
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, LabelList, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// Read the colour tokens from CSS so light/dark mode stay in one place (theme.css).
const TOKENS = ["--series-1", "--series-2", "--surface-1", "--text-primary", "--text-secondary", "--text-muted", "--grid", "--axis"];

function readTokens() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t.slice(2), style.getPropertyValue(t).trim()]));
}

export function useChartColors() {
  const [colors, setColors] = useState(readTokens);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setColors(readTokens());
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return colors;
}

// Tooltip: the value is the strong element, the label is secondary.
function ChartTooltip({ active, payload, label, formatLabel }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="muted small">{formatLabel ? formatLabel(label) : label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="tooltip-row">
          <span className="line-key" style={{ background: p.color }} />
          <strong>{p.value}</strong> <span className="muted small">{p.name}</span>
        </div>
      ))}
    </div>
  );
}

// A card with a title, the chart, and a button to switch to a plain table.
export function ChartCard({ title, subtitle, rows, columns, children }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="card chart-card">
      <div className="chart-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="muted small">{subtitle}</p>}
        </div>
        <button className="link small" onClick={() => setAsTable(!asTable)}>{asTable ? "Chart" : "Table"}</button>
      </div>
      {asTable ? (
        <table className="table compact">
          <thead><tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>{columns.map(([key]) => <td key={key}>{row[key]}</td>)}</tr>
            ))}
          </tbody>
        </table>
      ) : rows.length ? children : <p className="muted">No data yet.</p>}
    </section>
  );
}

// Horizontal bars for "count per category/block": one series, so one colour and no legend.
export function HorizontalBars({ data, labelKey = "label", valueKey = "count", name = "Complaints" }) {
  const c = useChartColors();
  const height = Math.max(160, data.length * 34 + 30);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 8 }} barCategoryGap={6}>
        <CartesianGrid horizontal={false} stroke={c.grid} />
        <XAxis type="number" allowDecimals={false} stroke={c.axis} tick={{ fill: c["text-muted"], fontSize: 12 }} />
        <YAxis type="category" dataKey={labelKey} width={150} stroke={c.axis} tick={{ fill: c["text-secondary"], fontSize: 12 }} />
        <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={<ChartTooltip />} />
        <Bar dataKey={valueKey} name={name} fill={c["series-1"]} radius={[0, 4, 4, 0]} maxBarSize={24} isAnimationActive={false}>
          <LabelList dataKey={valueKey} position="right" fill={c["text-secondary"]} fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Line over time: 2px line, dots with a surface ring, crosshair tooltip.
export function TrendLine({ data, xKey, valueKey = "count", name = "Complaints", formatX }) {
  const c = useChartColors();
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 12, right: 24, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey={xKey} tickFormatter={formatX} stroke={c.axis} tick={{ fill: c["text-muted"], fontSize: 12 }} />
        <YAxis allowDecimals={false} stroke={c.axis} tick={{ fill: c["text-muted"], fontSize: 12 }} width={36} />
        <Tooltip cursor={{ stroke: c.axis, strokeWidth: 1 }} content={<ChartTooltip formatLabel={formatX} />} />
        <Line type="monotone" dataKey={valueKey} name={name} stroke={c["series-1"]} strokeWidth={2}
              dot={{ r: 4, fill: c["series-1"], stroke: c["surface-1"], strokeWidth: 2 }} activeDot={{ r: 6 }}
              isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Grouped bars for comparing two models (two series -> legend).
export function CompareBars({ data, series }) {
  const c = useChartColors();
  const colors = [c["series-1"], c["series-2"]];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 4, left: 0 }} barGap={2}>
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="metric" stroke={c.axis} tick={{ fill: c["text-secondary"], fontSize: 12 }} />
        <YAxis domain={[0, 100]} unit="%" stroke={c.axis} tick={{ fill: c["text-muted"], fontSize: 12 }} width={44} />
        <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={<ChartTooltip />} />
        {/* Legend text uses the normal text colour; the coloured square next to it identifies the series. */}
        <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => <span style={{ color: c["text-secondary"] }}>{value}</span>} />
        {series.map(([key, name], i) => (
          <Bar key={key} dataKey={key} name={name} fill={colors[i]} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
            <LabelList dataKey={key} position="top" fill={c["text-secondary"]} fontSize={11} formatter={(v) => (v == null ? "" : `${v}%`)} />
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

// A number with a label (used for headline figures).
export function StatTile({ label, value, hint }) {
  return (
    <div className="stat-tile">
      <div className="muted small">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="muted small">{hint}</div>}
    </div>
  );
}
