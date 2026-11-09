import React from "react";
import {
  formatDate,
  formatNumber,
  metricLabel,
  metricValue,
  formatPace,
  paceWithUnit,
} from "./format";
export const tooltipStyle = {
  background: "var(--surface-raised)",
  border: "1px solid var(--border-strong)",
  borderRadius: 8,
  color: "var(--text)",
  fontSize: 12,
};
export function ChartTooltip({
  active,
  payload,
  label,
  x = "date",
  names = {},
  format,
  metric,
  normalized = false,
  xMetric,
}: {
  active?: boolean;
  payload?: any[];
  label?: unknown;
  x?: string;
  names?: Record<string, string>;
  format?: (v: any) => string;
  metric?: string;
  normalized?: boolean;
  xMetric?: string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload || {};
  const heading =
    point.displayName ||
    (point.date || x === "date"
      ? formatDate(point.date || label)
      : `${metricLabel(x)} · ${metricValue(x, Number(label))}`);
  return (
    <div className="stride-tooltip" style={tooltipStyle}>
      <strong>{heading}</strong>
      {point.evidence && <small>{point.evidence}</small>}
      {payload.map((p, i) => {
        const key = String(p.dataKey),
          field = key === "x" ? xMetric || x : metric || key;
        return (
          <div key={key + i}>
            <i style={{ background: p.color || "var(--accent)" }} />
            <span>
              {names[key] || metricLabel(key === "x" ? xMetric || x : key)}
            </span>
            <b>
              {normalized
                ? formatNumber(p.value, 1) + " SD"
                : format
                  ? format === formatPace
                    ? paceWithUnit(p.value)
                    : format(p.value)
                  : metricValue(field, p.value)}
            </b>
          </div>
        );
      })}
      {point.seconds != null && (
        <small>Matched samples: {metricValue("seconds", point.seconds)}</small>
      )}
    </div>
  );
}
