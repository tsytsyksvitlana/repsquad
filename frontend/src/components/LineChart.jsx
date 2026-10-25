import { fmtDay, fmtShortDay, num } from "../utils/format.js";

const LABELS = { best_1rm: "1RM, кг", max_weight_kg: "кг", volume_kg: "кг", max_reps: "повт." };

/** Simple SVG line chart of one metric across workouts. points: [{ date, [metric]: number }]. */
export default function LineChart({ points, metric }) {
  const W = 720, H = 260, pad = { l: 46, r: 16, t: 14, b: 30 };
  const values = points.map((p) => p[metric]);
  let lo = Math.min(...values), hi = Math.max(...values);
  if (lo === hi) { lo -= 1; hi += 1; }
  const margin = (hi - lo) * 0.15;
  lo = Math.max(0, lo - margin); hi += margin;
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const x = (i) => pad.l + (points.length === 1 ? iw / 2 : (i * iw) / (points.length - 1));
  const y = (v) => pad.t + ih * (1 - (v - lo) / (hi - lo));
  const ticks = [0, 1, 2, 3, 4].map((k) => lo + ((hi - lo) * k) / 4);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[metric]).toFixed(1)}`).join(" ");
  const area = points.length > 1 ? `${path} L${x(points.length - 1).toFixed(1)},${pad.t + ih} L${x(0).toFixed(1)},${pad.t + ih} Z` : "";
  const every = Math.ceil(points.length / 6);

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Графік: ${LABELS[metric]}, ${points.length} тренувань`}>
      {ticks.map((t, i) => (
        <g key={i}>
          <line className="grid" x1={pad.l} x2={W - pad.r} y1={y(t).toFixed(1)} y2={y(t).toFixed(1)} />
          <text className="axis" x={pad.l - 6} y={(y(t) + 4).toFixed(1)} textAnchor="end">{num(Math.round(t * 10) / 10)}</text>
        </g>
      ))}
      {area && <path className="area" d={area} />}
      {points.length > 1 && <path className="line" d={path} />}
      {points.map((p, i) => (
        <g key={i}>
          <circle className="dot" cx={x(i).toFixed(1)} cy={y(p[metric]).toFixed(1)} r="5">
            <title>{`${fmtDay(p.date)}: ${num(p[metric])} ${LABELS[metric]}`}</title>
          </circle>
          {(i % every === 0 || i === points.length - 1) && (
            <text className="axis" x={x(i).toFixed(1)} y={H - 8} textAnchor={points.length > 1 && i === points.length - 1 ? "end" : "middle"}>
              {fmtShortDay(p.date)}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
