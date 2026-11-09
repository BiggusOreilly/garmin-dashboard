import React, { useState } from "react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  formatDate,
  formatDistance,
  paceWithUnit,
  formatHeartRate,
  formatDuration,
  formatNumber,
  orderRuns,
  runLabels,
} from "./format";
import { colors, chartTokens } from "./appearance";
import { tooltipStyle } from "./chart-ui";
export function hrBins(records: any[]) {
  const bins = new Map<
    number,
    { seconds: number; speed: number; hr: number; count: number }
  >();
  for (let i = 1; i < records.length; i++) {
    const a = records[i - 1],
      b = records[i],
      dt = b.t - a.t;
    if (
      !(
        dt > 0 &&
        dt <= 10 &&
        b.speed >= 0.5 &&
        b.speed <= 10 &&
        b.hr >= 35 &&
        b.hr <= 220
      )
    )
      continue;
    const band = Math.floor(b.hr / 5) * 5;
    const row = bins.get(band) || { seconds: 0, speed: 0, hr: 0, count: 0 };
    row.seconds += dt;
    row.speed += b.speed * dt;
    row.hr += b.hr * dt;
    row.count++;
    bins.set(band, row);
  }
  return [...bins]
    .filter(([, v]) => v.seconds >= 30)
    .sort(([a], [b]) => a - b)
    .map(([band, v]) => ({
      hr: v.hr / v.seconds,
      pace: 1000 / (v.speed / v.seconds),
      seconds: v.seconds,
      count: v.count,
      band: `${band}–${band + 5} bpm`,
    }));
}
function RelationshipTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: any[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="stride-tooltip" style={tooltipStyle}>
      <strong>{p.displayName || p.band || formatDate(p.date)}</strong>
      <div>
        Pace <b>{paceWithUnit(p.pace)}</b>
      </div>
      <div>
        Heart rate <b>{formatHeartRate(p.hr)}</b>
      </div>
      {p.distance != null && (
        <div>
          Distance <b>{formatDistance(p.distance)}</b>
        </div>
      )}
      {p.seconds != null && (
        <small>
          {formatDuration(p.seconds)} covered · {formatNumber(p.count)} paired
          samples
        </small>
      )}
    </div>
  );
}
export function RunRelationship({
  streams,
}: {
  streams: { run: any; records: any[] }[];
}) {
  const [mode, setMode] = useState("binned");
  const runs = orderRuns(streams.map((s) => s.run));
  const labels = runLabels(runs);
  const series = runs.map((run) => {
    const records = streams.find((s) => s.run.id === run.id)?.records || [];
    return {
      run,
      data:
        mode === "binned"
          ? hrBins(records)
          : records
              .filter(
                (p: any) =>
                  p.speed >= 0.5 && p.speed <= 10 && p.hr >= 35 && p.hr <= 220,
              )
              .filter(
                (_: any, i: number) =>
                  i % Math.max(1, Math.ceil(records.length / 300)) === 0,
              )
              .map((p: any) => ({ hr: p.hr, pace: 1000 / p.speed })),
      total: records.length,
    };
  });
  return (
    <>
      <div className="chart-mode">
        <button
          aria-pressed={mode === "binned"}
          onClick={() => setMode("binned")}
        >
          HR-band averages
        </button>
        <button
          aria-pressed={mode === "samples"}
          onClick={() => setMode("samples")}
        >
          Recorded samples
        </button>
      </div>
      <p className="relationship-note">
        {mode === "binned"
          ? "What pace did each run sustain in each 5 bpm band? Time-weighted speed, converted to pace; each bin needs at least 30 seconds of paired data. These within-run bins include warm-up; use Aerobic Efficiency for warm-up-excluded trends."
          : "Recorded paired measurements, limited to 300 display points per run. No smoothing or inferred trend. Low movement, invalid HR and gaps are omitted."}{" "}
        Weather, terrain and HR lag can affect this relationship.
      </p>
      <div className="analysis-chart">
        <ResponsiveContainer>
          <ScatterChart margin={{ left: 4, right: 20, bottom: 25, top: 15 }}>
            <CartesianGrid stroke={chartTokens.grid} />
            <XAxis
              dataKey="hr"
              type="number"
              name="Heart rate"
              domain={["auto", "auto"]}
              tickFormatter={(v) => formatHeartRate(v)}
              tick={{ fill: chartTokens.text, fontSize: 11 }}
              label={{
                value: "Heart rate (bpm)",
                position: "insideBottom",
                offset: -17,
                fill: chartTokens.text,
                fontSize: 11,
              }}
            />
            <YAxis
              dataKey="pace"
              type="number"
              name="Pace"
              width={73}
              reversed
              domain={["auto", "auto"]}
              tickFormatter={(v) => paceWithUnit(v)}
              tick={{ fill: chartTokens.text, fontSize: 11 }}
            />
            <Tooltip content={<RelationshipTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 20 }} />
            {series.map(({ run, data }, i) => (
              <Scatter
                key={run.id}
                name={labels[run.id]}
                fill={colors[i]}
                line={mode === "binned"}
                data={data.map((p: any) => ({
                  ...p,
                  displayName: labels[run.id] + (p.band ? " · " + p.band : ""),
                }))}
                isAnimationActive={false}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="caption">
        {series
          .map(
            (s) =>
              `${labels[s.run.id]}: ${formatNumber(s.data.length)} ${mode === "binned" ? "qualifying bands" : "display samples"}`,
          )
          .join(" · ")}
        . Lower pace time at the same HR can indicate better efficiency under
        comparable conditions. This is not a causal or grade-adjusted model.
      </p>
    </>
  );
}
export function TrainingRelationship({
  runs,
  open,
  go,
}: {
  runs: any[];
  open: (r: any) => void;
  go: (s: string) => void;
}) {
  const [mode, setMode] = useState("runs");
  const sorted = orderRuns(runs.filter((r) => r.hr && r.pace));
  const midpoint = sorted[Math.floor(sorted.length / 2)]?.date;
  const groups = [
    { name: "Earlier runs", data: sorted.filter((r) => r.date < midpoint) },
    { name: "Recent runs", data: sorted.filter((r) => r.date >= midpoint) },
  ];
  const matched = sorted
    .filter((r) => r.bands?.hr?.["150"])
    .map((r) => ({ ...r, aerobic: r.bands.hr["150"].value }));
  return (
    <>
      <div className="chart-mode">
        <button aria-pressed={mode === "runs"} onClick={() => setMode("runs")}>
          Individual runs
        </button>
        <button
          aria-pressed={mode === "trend"}
          onClick={() => setMode("trend")}
        >
          Matched-HR trend
        </button>
      </div>
      <p className="relationship-note">
        {mode === "runs"
          ? "How do run-average pace and HR differ between earlier and recent sessions? Global distance and classification filters help compare like sessions. Points include date, distance and effort; mixed intensities are not a fitness estimate."
          : "Am I faster at 150–155 bpm? Uses cached stable samples after warm-up. Each run needs three matched minutes. No line is fitted to an inadequate sample."}
      </p>
      <div className="analysis-chart">
        <ResponsiveContainer>
          {mode === "runs" ? (
            <ScatterChart margin={{ left: 0, right: 20, bottom: 25, top: 10 }}>
              <CartesianGrid stroke={chartTokens.grid} />
              <XAxis
                dataKey="pace"
                type="number"
                name="Pace"
                domain={["auto", "auto"]}
                tickFormatter={(v) => paceWithUnit(v)}
                tick={{ fill: chartTokens.text, fontSize: 11 }}
              />
              <YAxis
                dataKey="hr"
                type="number"
                name="Heart rate"
                domain={["auto", "auto"]}
                tickFormatter={(v) => formatHeartRate(v)}
                tick={{ fill: chartTokens.text, fontSize: 11 }}
                width={65}
              />
              <Tooltip content={<RelationshipTooltip />} />
              <Legend />
              {groups.map((g, i) => (
                <Scatter
                  key={g.name}
                  name={g.name}
                  fill={colors[i]}
                  data={g.data}
                  isAnimationActive={false}
                  onClick={(p: any) => open(p)}
                />
              ))}
            </ScatterChart>
          ) : (
            <LineChart
              data={matched}
              margin={{ left: 15, right: 20, bottom: 20, top: 10 }}
            >
              <CartesianGrid stroke={chartTokens.grid} />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => formatDate(v, "compact")}
                minTickGap={40}
                tick={{ fill: chartTokens.text, fontSize: 11 }}
              />
              <YAxis
                dataKey="aerobic"
                tickFormatter={(v) => paceWithUnit(v)}
                width={65}
                domain={["auto", "auto"]}
                tick={{ fill: chartTokens.text, fontSize: 11 }}
              />
              <Tooltip
                content={({ active, payload }: any) =>
                  active && payload?.length ? (
                    <div className="stride-tooltip" style={tooltipStyle}>
                      <strong>{formatDate(payload[0].payload.date)}</strong>
                      <div>
                        Pace at 150–155 bpm{" "}
                        <b>{paceWithUnit(payload[0].value)}</b>
                      </div>
                    </div>
                  ) : null
                }
              />
              <Line
                dataKey="aerobic"
                name="Pace at 150–155 bpm"
                stroke={colors[0]}
                connectNulls={false}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
      {mode === "trend" && matched.length < 3 && (
        <p className="caption">
          Insufficient matched runs for a trend comparison ({matched.length}{" "}
          available).
        </p>
      )}
      <button className="text-button" onClick={() => go("Aerobic Efficiency")}>
        Explore matched-HR analysis and sample counts →
      </button>
    </>
  );
}
