// Campus map: buildings as labelled squares, hotspots as circles (bigger = more complaints).
// Coordinates are metres from the main gate (backend ai/campus.py). North is up.
import { categoryLabel } from "../constants.js";

const PAD = 70; // metres of empty space around the campus
const NEAR = 40; // hotspots closer than this (metres) are spread out so they don't hide each other

// Hotspots of different categories can share the same buildings. Spread each group of
// nearby hotspots around their shared centre, so every circle stays visible.
function spreadOut(hotspots) {
  const groups = [];
  hotspots.forEach((h, i) => {
    const group = groups.find((g) => Math.hypot(g.x - h.center.x, g.y - h.center.y) < NEAR);
    if (group) group.items.push(i);
    else groups.push({ x: h.center.x, y: h.center.y, items: [i] });
  });
  const positions = [];
  for (const g of groups) {
    g.items.forEach((index, k) => {
      const angle = (2 * Math.PI * k) / g.items.length - Math.PI / 2;
      const distance = g.items.length > 1 ? 34 : 0;
      positions[index] = { x: g.x + distance * Math.cos(angle), y: g.y - distance * Math.sin(angle) };
    });
  }
  return positions;
}

export default function CampusMap({ campus, hotspots, active, onActivate }) {
  if (!campus?.length) return null;
  const xs = campus.map((p) => p.x);
  const ys = campus.map((p) => p.y);
  const minX = Math.min(...xs) - PAD, maxX = Math.max(...xs) + PAD;
  const minY = Math.min(...ys) - PAD, maxY = Math.max(...ys) + PAD;
  const width = maxX - minX, height = maxY - minY;
  // SVG y grows downwards; flip so that larger y (north) is at the top.
  const sx = (x) => x - minX;
  const sy = (y) => maxY - y;
  const biggest = Math.max(1, ...hotspots.map((h) => h.count));
  const positions = spreadOut(hotspots);
  const radius = (h) => 12 + 26 * Math.sqrt(h.count / biggest); // area grows with the count

  return (
    <figure className="campus-map">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Campus map with complaint hotspots">
        <rect x="0" y="0" width={width} height={height} rx="16" className="map-ground" />
        {/* 1. hotspot circles (underneath) */}
        {hotspots.map((h, i) => (
          <g key={`c${i}`} className={`map-hotspot ${active === i ? "active" : ""}`}
             onMouseEnter={() => onActivate(i)} onMouseLeave={() => onActivate(null)}
             onFocus={() => onActivate(i)} onBlur={() => onActivate(null)} tabIndex={0}>
            <title>{`${categoryLabel(h.category)}: ${h.count} complaints (${h.open_count} open)`}</title>
            <circle cx={sx(positions[i].x)} cy={sy(positions[i].y)} r={radius(h)} />
          </g>
        ))}
        {/* 2. buildings and their names */}
        {campus.map((p) => (
          <g key={p.name} className="map-place">
            <title>{p.name}</title>
            <rect x={sx(p.x) - 7} y={sy(p.y) - 7} width="14" height="14" rx="3" className="map-building" />
            {/* short block name keeps neighbouring labels apart; the full name is in the tooltip */}
            <text x={sx(p.x)} y={sy(p.y) + 22} className="map-label" textAnchor="middle">{p.block}</text>
          </g>
        ))}
        {/* 3. count badges on top, at the top-right edge of each circle */}
        {hotspots.map((h, i) => {
          const r = radius(h);
          const bx = sx(positions[i].x) + r * 0.7;
          const by = sy(positions[i].y) - r * 0.7;
          return (
            <g key={`b${i}`} className={`map-badge ${active === i ? "active" : ""}`} pointerEvents="none">
              <rect x={bx - 15} y={by - 10} width="30" height="20" rx="10" />
              <text x={bx} y={by + 4} textAnchor="middle">{h.count}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="muted small">
        Each circle is a hotspot (DBSCAN cluster). Its size shows the number of complaints. Hover a circle or a card to link them.
      </figcaption>
    </figure>
  );
}
