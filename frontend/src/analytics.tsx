import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ScatterChart,
  Scatter,
} from "recharts";

export type Point = Record<string, any>;
export const categories = [
  "Recovery",
  "Easy",
  "Aerobic",
  "Long",
  "Steady",
  "Tempo",
  "Threshold",
  "Intervals",
  "VO2 / high intensity",
  "Race / time trial",
  "Mixed / unclassified",
];
const colors = ["#bce68b", "#86b7ca", "#d5ad7c", "#a5a0d5", "#d18e99"];
const fmt = (v: any, d = 1) =>
  v == null
    ? "—"
    : Number(v).toLocaleString("en-AU", { maximumFractionDigits: d });
const pace = (v: any) =>
  v == null
    ? "—"
    : `${Math.floor(Math.round(v) / 60)}:${String(Math.round(v) % 60).padStart(2, "0")}`;
const time = (v: any) =>
  v == null || !Number.isFinite(v)
    ? "—"
    : `${Math.floor(v / 60)}:${String(Math.round(v) % 60).padStart(2, "0")}`;
const mean = (a: number[]) =>
  a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
const shift = (d: string, n: number) => {
  const x = new Date(d + "T12:00:00");
  x.setDate(x.getDate() + n);
  return localDate(x);
};
const localDate = (x: Date) =>
  `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
export function Panel({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card analysis-panel">
      <div className="card-head">
        <div>
          <h3>{title}</h3>
          {sub && <p>{sub}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}
function Empty() {
  return <div className="chart-empty">Insufficient reliable data</div>;
}
function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="analysis-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
export function Plot({
  data,
  keys,
  x = "date",
  format,
  open,
  scatter = false,
}: {
  data: Point[];
  keys: string[];
  x?: string;
  format?: (v: any) => string;
  open?: (id: string) => void;
  scatter?: boolean;
}) {
  if (!data.some((p) => keys.some((k) => p[k] != null))) return <Empty />;
  return (
    <div className="analysis-chart">
      <ResponsiveContainer width="100%" height="100%">
        {scatter ? (
          <ScatterChart margin={{ left: 0, right: 20, bottom: 20, top: 10 }}>
            <CartesianGrid stroke="#29352d" />
            <XAxis
              dataKey={x}
              name={x}
              type="number"
              tickFormatter={x === "pace" ? pace : undefined}
              domain={["auto", "auto"]}
            />
            <YAxis
              dataKey={keys[0]}
              name={keys[0]}
              type="number"
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "#19221c",
                border: "1px solid #435044",
              }}
            />
            <Scatter data={data} fill={colors[0]} isAnimationActive={false} />
          </ScatterChart>
        ) : (
          <LineChart
            data={data}
            margin={{ left: 0, right: 18, bottom: 12, top: 10 }}
            onClick={(e: any) => {
              const index = e?.activeTooltipIndex ?? e?.activeIndex;
              const p =
                e?.activePayload?.[0]?.payload ??
                (index != null ? data[Number(index)] : null);
              if (p?.id && open) open(p.id);
            }}
          >
            <CartesianGrid
              stroke="#29352d"
              vertical={false}
              strokeDasharray="3 5"
            />
            <XAxis
              dataKey={x}
              minTickGap={35}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) =>
                x === "date" ? String(v).slice(5) : fmt(v)
              }
            />
            <YAxis
              width={52}
              tick={{ fontSize: 11 }}
              domain={["auto", "auto"]}
              tickFormatter={format}
            />
            <Tooltip
              contentStyle={{
                background: "#19221c",
                border: "1px solid #435044",
                borderRadius: 8,
              }}
              formatter={(v: any) => (format ? format(v) : fmt(v))}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
            {keys.map((k, i) => (
              <Line
                key={k}
                dataKey={k}
                name={k}
                stroke={colors[i % colors.length]}
                strokeWidth={i ? 1.6 : 2.2}
                dot={data.length < 80 ? { r: 2 } : false}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
export function InsightList({
  items,
  go,
  limit = 12,
}: {
  items: Point[];
  go: (s: string) => void;
  limit?: number;
}) {
  return (
    <Panel
      title="What your data shows"
      sub="Local, deterministic observations · only when samples and changes are sufficient"
    >
      {items.length ? (
        items.slice(0, limit).map((i) => (
          <button className="insight-row" key={i.id} onClick={() => go(i.page)}>
            <span className="insight-mark">→</span>
            <span>
              <strong>{i.text}</strong>
              <small>{i.evidence}</small>
            </span>
            <span>→</span>
          </button>
        ))
      ) : (
        <p className="caption">
          No observations meet the evidence threshold in this period. More
          comparable runs may reveal a meaningful change.
        </p>
      )}
    </Panel>
  );
}
function bandPoints(runs: Point[], mode: string, band: string) {
  return [...runs]
    .reverse()
    .filter((r) => r.bands?.[mode]?.[band])
    .map((r) => ({
      date: r.date,
      id: r.id,
      value: r.bands[mode][band].value,
      seconds: r.bands[mode][band].seconds,
    }));
}
function rolling(points: Point[], days = 28) {
  return points.map((p) => ({
    ...p,
    rolling: mean(
      points
        .filter((q) => q.date <= p.date && q.date >= shift(p.date, -days + 1))
        .map((q) => q.value),
    ),
  }));
}
function change(points: Point[], end: string, days: number) {
  const a = points.filter(
      (p) => p.date >= shift(end, -days + 1) && p.date <= end,
    ),
    b = points.filter(
      (p) =>
        p.date >= shift(end, -2 * days + 1) && p.date < shift(end, -days + 1),
    );
  return {
    value:
      a.length >= 3 && b.length >= 3
        ? mean(a.map((p) => p.value))! - mean(b.map((p) => p.value))!
        : null,
    a: a.length,
    b: b.length,
  };
}
export function BandAnalysis({
  runs,
  allRuns,
  mode,
  end,
  open,
}: {
  runs: Point[];
  allRuns: Point[];
  mode: "hr" | "pace";
  end: string;
  open: (s: string) => void;
}) {
  const [band, setBand] = useState(
    () =>
      sessionStorage.getItem("stride-band-" + mode) ||
      (mode === "hr" ? "150" : "330"),
  );
  const [min, setMin] = useState(""),
    [max, setMax] = useState("");
  const points = bandPoints(
    runs.filter(
      (r) =>
        (!min || r.duration >= +min * 60) && (!max || r.duration <= +max * 60),
    ),
    mode,
    band,
  );
  const history = bandPoints(
    allRuns.filter(
      (r) =>
        (!min || r.duration >= +min * 60) && (!max || r.duration <= +max * 60),
    ),
    mode,
    band,
  );
  const f = mode === "hr" ? pace : (v: any) => fmt(v) + " bpm";
  const choices =
    mode === "hr"
      ? Array.from({ length: 20 }, (_, i) => 100 + i * 5)
      : Array.from({ length: 29 }, (_, i) => 180 + i * 15);
  const c4 = change(history, end, 28),
    c12 = change(history, end, 84),
    recent = points.filter((p) => p.date >= shift(end, -27));
  return (
    <>
      <Panel
        title={
          mode === "hr"
            ? "Pace at comparable heart rate"
            : "Heart rate at comparable pace"
        }
        sub="Recorded FIT samples · 10-minute warm-up removed · ≥30-second continuous bouts · ≥3 matched minutes per run"
      >
        <div className="analysis-controls">
          <label>
            {mode === "hr" ? "HR band" : "Pace band"}
            <select
              aria-label={mode === "hr" ? "HR band" : "Pace band"}
              value={band}
              onChange={(e) => {
                setBand(e.target.value);
                sessionStorage.setItem("stride-band-" + mode, e.target.value);
              }}
            >
              {choices.map((v) => (
                <option key={v} value={v}>
                  {mode === "hr"
                    ? `${v}–${v + 5} bpm`
                    : `${pace(v)}–${pace(v + 15)}/km`}
                </option>
              ))}
            </select>
          </label>
          <label>
            Minimum minutes
            <input
              aria-label="Minimum duration minutes"
              type="number"
              min="0"
              value={min}
              onChange={(e) => setMin(e.target.value)}
            />
          </label>
          <label>
            Maximum minutes
            <input
              aria-label="Maximum duration minutes"
              type="number"
              min="0"
              value={max}
              onChange={(e) => setMax(e.target.value)}
            />
          </label>
        </div>
        <div className="analysis-stats">
          <Stat
            label="4-week change"
            value={
              c4.value == null
                ? "Insufficient reliable data"
                : `${c4.value > 0 ? "+" : ""}${fmt(c4.value)} ${mode === "hr" ? "sec/km" : "bpm"}`
            }
            note={`${c4.a} recent / ${c4.b} previous runs`}
          />
          <Stat
            label="12-week change"
            value={
              c12.value == null
                ? "Insufficient reliable data"
                : `${c12.value > 0 ? "+" : ""}${fmt(c12.value)} ${mode === "hr" ? "sec/km" : "bpm"}`
            }
            note={`${c12.a} recent / ${c12.b} previous runs`}
          />
          <Stat
            label="Best recent"
            value={
              recent.length >= 3
                ? f(Math.min(...recent.map((p) => p.value)))
                : "—"
            }
            note="Last 28 days · ≥3 qualifying runs"
          />
          <Stat
            label="Sample strength"
            value={`${points.length} runs`}
            note={`${fmt(points.reduce((s, p) => s + p.seconds, 0) / 60)} matched minutes · ${points.length >= 10 ? "more evidence" : points.length >= 3 ? "limited evidence" : "low sample"}`}
          />
        </div>
        <Plot
          data={rolling(points)}
          keys={["value", "rolling"]}
          format={f}
          open={open}
        />
        <p className="caption">
          Lower is better in both views. Rolling line is a 28-day mean;
          single-run points remain visible. Changes need ≥3 runs in each
          non-overlapping window. The selected HR band includes its lower bound
          and excludes its upper bound. Terrain, weather and sensor differences
          remain confounders.
        </p>
      </Panel>
      <Panel
        title="Qualifying runs"
        sub="Select a row to inspect the source activity"
      >
        <div className="evidence-list">
          {points
            .slice()
            .reverse()
            .map((p) => (
              <button key={p.id} onClick={() => open(p.id)}>
                <span>{p.date}</span>
                <strong>{f(p.value)}</strong>
                <small>{fmt(p.seconds / 60)} matched min →</small>
              </button>
            ))}
        </div>
        {!points.length && <Empty />}
      </Panel>
    </>
  );
}
export function Fitness({
  runs,
  allRuns,
  end,
  open,
}: {
  runs: Point[];
  allRuns: Point[];
  end: string;
  open: (s: string) => void;
}) {
  const components = [
    {
      title: "Aerobic pace · 150–155 bpm",
      mode: "hr",
      band: "150",
      unit: "sec/km",
      f: pace,
    },
    {
      title: "HR at 5:30–5:45/km",
      mode: "pace",
      band: "330",
      unit: "bpm",
      f: fmt,
    },
    { title: "Aerobic decoupling", mode: "drift", band: "", unit: "%", f: fmt },
    {
      title: "Best 5 km segment",
      mode: "five",
      band: "",
      unit: "sec",
      f: time,
    },
  ];
  function points(rs: Point[], c: Point) {
    return c.mode === "drift"
      ? [...rs]
          .reverse()
          .filter((r) => r.metrics?.drift?.value != null)
          .map((r) => ({
            date: r.date,
            id: r.id,
            value: r.metrics.drift.value,
          }))
      : c.mode === "five"
        ? [...rs]
            .reverse()
            .filter((r) => r.records?.["5 km"] && !r.records["5 km"].flag)
            .map((r) => ({
              date: r.date,
              id: r.id,
              value: r.records["5 km"].seconds,
            }))
        : bandPoints(rs, c.mode, c.band);
  }
  return (
    <>
      <div className="method-note">
        <p>
          Fitness is shown as observable components. Lower values can indicate
          progress under comparable conditions. No composite score or Garmin VO2
          max is required. Missing components remain unavailable.
        </p>
      </div>
      <div className="grid two">
        {components.map((c) => {
          const p = points(runs, c),
            h = points(allRuns, c);
          return (
            <Panel
              key={c.title}
              title={c.title}
              sub="Select a point to open the source run"
            >
              <div className="analysis-stats">
                {[28, 84, 183].map((d) => {
                  const t = change(h, end, d);
                  return (
                    <Stat
                      key={d}
                      label={
                        d === 28
                          ? "Short term · 4 weeks"
                          : d === 84
                            ? "Medium term · 12 weeks"
                            : "Longer term · 6 months"
                      }
                      value={
                        t.value == null
                          ? "—"
                          : `${t.value > 0 ? "+" : ""}${fmt(t.value)} ${c.unit}`
                      }
                      note={`${t.a} recent / ${t.b} previous runs`}
                    />
                  );
                })}
              </div>
              <Plot
                data={rolling(p)}
                keys={["value", "rolling"]}
                format={c.f}
                open={open}
              />
            </Panel>
          );
        })}
        <Panel
          title="Longer-run efficiency"
          sub="Runs ≥60 minutes · observed speed/HR ratio, not a fitness score"
        >
          <Plot
            data={[...runs]
              .reverse()
              .filter((r) => r.duration >= 3600 && r.pace && r.hr)
              .map((r) => ({
                date: r.date,
                id: r.id,
                efficiency: 1000 / r.pace / r.hr,
              }))}
            keys={["efficiency"]}
            format={(v) => fmt(v, 4)}
            open={open}
          />
        </Panel>
        <Panel
          title="Cadence stability"
          sub="Second-half cadence minus first-half · steps/min"
        >
          <Plot
            data={[...runs].reverse().map((r) => ({
              date: r.date,
              id: r.id,
              change: r.metrics?.cadenceChange,
            }))}
            keys={["change"]}
            open={open}
          />
        </Panel>
      </div>
    </>
  );
}
export function Records({
  data,
  runs,
  open,
  five = false,
  end,
}: {
  data: Point;
  runs: Point[];
  open: (s: string) => void;
  five?: boolean;
  end: string;
}) {
  const [distance, setDistance] = useState("5 km");
  const progression = data.records || {};
  const events = progression[five ? "5 km" : distance] || [];
  const qualifying = runs.filter((r) => r.records?.["5 km"]);
  const recent = qualifying.filter(
    (r) => r.date >= shift(end, -27) && !r.records["5 km"].flag,
  );
  return (
    <>
      {five ? (
        <div className="analysis-stats featured">
          <Stat
            label="Current imported PB"
            value={time((progression["5 km"] || []).at(-1)?.seconds)}
            note="Reliable unflagged segments · all imported history"
          />
          <Stat
            label="Recent best"
            value={
              recent.length
                ? time(
                    Math.min(...recent.map((r) => r.records["5 km"].seconds)),
                  )
                : "—"
            }
            note="Last 28 days"
          />
          <Stat
            label="Valid 5 km performances"
            value={String(
              qualifying.filter((r) => !r.records["5 km"].flag).length,
            )}
            note="Within global filters"
          />
        </div>
      ) : (
        <Panel
          title="Personal records"
          sub="Best valid elapsed segments · imported history, not certified race records"
        >
          <div className="record-grid">
            {Object.entries(progression).map(([label, ev]: any) => {
              const p = ev.at(-1);
              return (
                <button
                  className="record-tile"
                  key={label}
                  onClick={() => {
                    setDistance(label);
                    if (p) open(p.id);
                  }}
                >
                  <span>{label}</span>
                  <strong>
                    {label === "Longest run"
                      ? p
                        ? fmt(p.distance / 1000) + " km"
                        : "—"
                      : time(p?.seconds)}
                  </strong>
                  <small>
                    {p ? `${p.date} · ${p.name}` : "Insufficient reliable data"}
                  </small>
                  <small>
                    {p && label !== "Longest run"
                      ? `Average pace ${pace(p.seconds / (({ "400 m": 0.4, "1 km": 1, "1 mile": 1.609344, "3 km": 3, "5 km": 5, "10 km": 10 } as Record<string, number>)[label] || 1))}/km`
                      : label === "Longest run"
                        ? "Recorded summary distance"
                        : "Sensor-validated segment"}
                  </small>
                  <small>
                    {p
                      ? `Average HR ${fmt(p.hr)} bpm · improvement ${p.improvement == null ? "first record" : label === "Longest run" ? fmt(p.improvement / 1000) + " km" : fmt(p.improvement) + " sec"}`
                      : label === "400 m"
                        ? "400 m requires ≤2-second sampling"
                        : "Requires reliable continuous distance samples"}
                  </small>
                </button>
              );
            })}
          </div>
        </Panel>
      )}
      <Panel
        title={five ? "5K PB progression" : "Record progression history"}
        sub="Each event is a new best in imported history · downhill >1% excluded"
      >
        {!five && (
          <label className="analysis-controls">
            Distance
            <select
              aria-label="Record distance"
              value={distance}
              onChange={(e) => setDistance(e.target.value)}
            >
              {Object.keys(progression).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
        )}
        <Plot
          data={events.map((p: Point) => ({
            ...p,
            result: p.seconds ?? p.distance / 1000,
          }))}
          keys={["result"]}
          format={distance === "Longest run" && !five ? fmt : time}
          open={open}
        />
        <div className="evidence-list">
          {events
            .slice()
            .reverse()
            .map((p: Point) => (
              <button key={p.id} onClick={() => open(p.id)}>
                <span>
                  {p.date} · {p.name}
                </span>
                <strong>
                  {p.seconds ? time(p.seconds) : fmt(p.distance / 1000) + " km"}
                </strong>
                <small>
                  {p.improvement == null
                    ? "First imported best"
                    : `${fmt(p.improvement)} ${p.seconds ? "sec" : "m"} improvement`}{" "}
                  →
                </small>
              </button>
            ))}
        </div>
      </Panel>
      {five && (
        <>
          <Panel
            title="5K fitness trend"
            sub="Best segment per run + 28-day rolling mean; incidental efforts are not race predictions"
          >
            <Plot
              data={rolling(
                [...qualifying]
                  .reverse()
                  .filter((r) => !r.records["5 km"].flag)
                  .map((r) => ({
                    id: r.id,
                    date: r.date,
                    value: r.records["5 km"].seconds,
                  })),
              )}
              keys={["value", "rolling"]}
              format={time}
              open={open}
            />
          </Panel>
          <Panel
            title="5K performances"
            sub="Whole 5K activities are identified by distance (4.95–5.10 km); title cues identify possible races/time trials"
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {[
                      "Run / source",
                      "5 km",
                      "HR avg / max",
                      "Cadence",
                      "Split CV",
                      "Second half",
                      "Final km",
                      "Quality",
                    ].map((x) => (
                      <th key={x}>{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {qualifying.map((r) => {
                    const p = r.records["5 km"];
                    return (
                      <tr key={r.id} onClick={() => open(r.id)}>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => open(r.id)}
                          >
                            {r.date} · {r.name}
                          </button>
                          <small className="block">
                            {r.classification?.label === "Race / time trial"
                              ? "Race / time-trial title cue"
                              : r.distance >= 4950 && r.distance <= 5100
                                ? "Recorded 5K activity"
                                : "Incidental segment"}
                          </small>
                        </td>
                        <td>{time(p.seconds)}</td>
                        <td>
                          {fmt(p.hr)} / {fmt(p.maxHR)}
                        </td>
                        <td>{fmt(p.cadence)}</td>
                        <td>{fmt(p.splitCV)}%</td>
                        <td>{fmt(p.halfChange)}%</td>
                        <td>{pace(p.finalKm)}</td>
                        <td>
                          {p.flag || p.terrain}
                          <small className="block">{p.precision}</small>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!qualifying.length && <Empty />}
          </Panel>
        </>
      )}
      {five && (
        <Panel
          title="Garmin-reported and summary-only 5K results"
          sub="Separate evidence tier; not added to sensor-validated PB progression"
        >
          <div className="evidence-list">
            {runs
              .filter(
                (r) =>
                  (r.fiveK || (r.distance >= 4950 && r.distance <= 5100)) &&
                  !r.records?.["5 km"],
              )
              .map((r) => (
                <button key={r.id} onClick={() => open(r.id)}>
                  <span>
                    {r.date} · {r.name}
                    <small className="block">
                      {r.fiveK
                        ? "Garmin-reported segment; underlying stream not validated"
                        : "Recorded activity near 5K; distance not standardised"}
                    </small>
                  </span>
                  <strong>{time(r.fiveK || r.duration)}</strong>
                  <small>
                    HR {fmt(r.hr)} / max {fmt(r.maxHR)} · cadence{" "}
                    {fmt(r.cadence)} →
                  </small>
                </button>
              ))}
          </div>
          {!runs.some(
            (r) =>
              (r.fiveK || (r.distance >= 4950 && r.distance <= 5100)) &&
              !r.records?.["5 km"],
          ) && (
            <p className="caption">
              No additional summary-only performances in these dates.
            </p>
          )}
        </Panel>
      )}
      <p className="caption">
        Segment ends are linearly interpolated from cumulative FIT distance.
        Gaps &gt;10s, pauses, distance resets and implausible movement
        disqualify candidates. Net downhill &gt;1% is flagged and excluded from
        PBs. Elevation availability is disclosed. Very short records are omitted
        with coarse sampling. Fastest average pace for each distance is segment
        time ÷ distance.
      </p>
    </>
  );
}
export function Training({
  training,
  start,
  end,
}: {
  training: Point;
  start: string;
  end: string;
}) {
  const weeks = (training.weekly || []).filter(
      (w: Point) => w.date <= end && shift(w.date, 6) >= start,
    ),
    daily = (training.daily || []).filter(
      (d: Point) => d.date >= start && d.date <= end,
    ),
    months = (training.monthly || []).filter(
      (d: Point) => d.date <= end && d.date >= start.slice(0, 7) + "-01",
    );
  return (
    <>
      <div className="grid two">
        <Panel
          title="Weekly distance"
          sub="Monday–Sunday; current week marked as incomplete"
        >
          <Plot data={weeks} keys={["km"]} />
        </Panel>
        <Panel
          title="Rolling volume"
          sub="7-day and 28-day distance · includes the selected date"
        >
          <Plot data={daily} keys={["rolling7", "rolling28"]} />
        </Panel>
        <Panel title="Monthly volume" sub="Calendar-month kilometres">
          <Plot data={months} keys={["km"]} />
        </Panel>
        <Panel
          title="Intensity-weighted minutes"
          sub="Derived load proxy: minutes in Garmin zone × zone number (1–5)"
        >
          <Plot data={weeks} keys={["zoneMinutes"]} />
          <p className="caption">
            Volume measures distance; intensity uses configured HR zones.
            Zone-weighted minutes are a descriptive proxy, not a validated
            physiological load or recovery prescription. No acute/chronic
            injury-risk ratio is inferred.
          </p>
        </Panel>
      </div>
      <Panel
        title="Volume progression"
        sub="An abrupt flag means >30% and ≥5 km above the preceding 4 complete calendar weeks; descriptive, not a safety threshold"
      >
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  "Week",
                  "Distance",
                  "Runs",
                  "Average",
                  "Longest",
                  "Long-run share",
                  "Week change",
                  "4-week baseline",
                  "Status",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {weeks
                .slice()
                .reverse()
                .map((w: Point) => (
                  <tr key={w.date}>
                    <td>{w.date}</td>
                    <td>{fmt(w.km)} km</td>
                    <td>{w.count}</td>
                    <td>{fmt(w.average)} km</td>
                    <td>{fmt(w.longest)} km</td>
                    <td>{fmt(w.longShare)}%</td>
                    <td>{fmt(w.change)}%</td>
                    <td>{fmt(w.baseline)} km</td>
                    <td>
                      {!w.complete
                        ? "Incomplete week"
                        : w.abrupt
                          ? "Abrupt increase"
                          : "—"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
export function Similar({
  run,
  runs,
  open,
  add,
}: {
  run: Point;
  runs: Point[];
  open: (s: string) => void;
  add: (s: string) => void;
}) {
  const [matches, setMatches] = useState<Point[]>([]),
    [failure, setFailure] = useState("");
  useEffect(() => {
    let active = true;
    setMatches([]);
    setFailure("");
    fetch("/api/similar/" + run.id)
      .then((r) => {
        if (!r.ok) throw Error("Could not read comparable runs.");
        return r.json();
      })
      .then((items: Point[]) => {
        if (active)
          setMatches(
            items.map((item) => ({
              ...runs.find((r) => r.id === item.id),
              ...item,
            })),
          );
      })
      .catch((e) => {
        if (active) setFailure(e.message);
      });
    return () => {
      active = false;
    };
  }, [run.id, runs.length]);

  return (
    <Panel
      title="Most comparable previous runs"
      sub="Distance ±25%, duration ±35%; ranked by distance, duration, HR, pace, ascent and classification. Route geometry is unavailable."
    >
      <div className="similar-list">
        {matches.map((r) => {
          const delta =
            run.hr && r.hr && run.pace && r.pace
              ? 100 * ((r.pace * r.hr) / (run.pace * run.hr) - 1)
              : null;
          return (
            <div key={r.id}>
              <button className="text-button" onClick={() => open(r.id)}>
                {r.date} · {r.name} →
              </button>
              <span className="small-tag">
                {delta == null
                  ? "Unavailable"
                  : delta > 2
                    ? "Better"
                    : delta < -2
                      ? "Worse"
                      : "Similar"}
                {delta != null ? ` · ${fmt(delta)}% speed/HR` : ""}
              </span>
              <p>
                Current vs previous: {pace(run.pace)} / {pace(r.pace)} per km ·{" "}
                {fmt(run.hr)} / {fmt(r.hr)} bpm · {fmt(run.cadence)} /{" "}
                {fmt(r.cadence)} spm · drift {fmt(run.metrics?.drift?.value)} /{" "}
                {fmt(r.metrics?.drift?.value)}% · late split{" "}
                {fmt(run.metrics?.splitChange)} / {fmt(r.metrics?.splitChange)}%
              </p>
              <button
                className="text-button"
                onClick={() => {
                  add(run.id);
                  add(r.id);
                }}
              >
                Add pair to comparison +
              </button>
            </div>
          );
        })}
      </div>
      {failure && <p className="error">{failure}</p>}
      {!matches.length && <Empty />}
      <p className="caption">
        Better/similar/worse describes the observed speed/HR ratio (±2%
        descriptive tolerance). It is not adjusted for heat, wind, surface or
        hills. Review the actual values and matched-band analyses.
      </p>
    </Panel>
  );
}
export function Comparison({
  runs,
  ids,
  setIds,
  open,
}: {
  runs: Point[];
  ids: string[];
  setIds: (ids: string[]) => void;
  open: (s: string) => void;
}) {
  const [details, setDetails] = useState<Record<string, Point>>({}),
    [error, setError] = useState(""),
    [axis, setAxis] = useState("percent"),
    [search, setSearch] = useState("");
  const selected = ids
    .map((id) => runs.find((r) => r.id === id))
    .filter(Boolean) as Point[];
  useEffect(() => {
    let active = true;
    setError("");
    Promise.all(
      ids.map(async (id) => {
        const res = await fetch("/api/run/" + id);
        if (!res.ok) throw Error("Could not load comparison streams.");
        return [id, await res.json()] as const;
      }),
    )
      .then((rs) => {
        if (active) setDetails(Object.fromEntries(rs));
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [ids.join(",")]);
  function data(field: string) {
    const points = Array.from({ length: 101 }, (_, i) => ({ x: i }) as Point);
    const maxKm = Math.max(...selected.map((r) => (r.distance || 0) / 1000), 1);
    for (const [i, r] of selected.entries()) {
      const records = details[r.id]?.series?.records || [];
      const maxT = records.at(-1)?.t || 1;
      let cursor = 0;
      for (let k = 0; k <= 100; k++) {
        const target = axis === "percent" ? (k * maxT) / 100 : k * maxKm * 10;
        const getX = (p: Point) =>
          axis === "percent" ? p.t : (p.distance ?? 0);
        while (cursor < records.length - 1 && getX(records[cursor]) < target)
          cursor++;
        const p = records[cursor];
        if (!p || Math.abs(getX(p) - target) > (axis === "percent" ? 15 : 100))
          continue;
        points[k][keys[i]] =
          field === "pace"
            ? p.speed >= 0.5 && p.speed <= 10
              ? 1000 / p.speed
              : null
            : field === "hr"
              ? p.hr >= 35 && p.hr <= 220
                ? p.hr
                : null
              : p[field];
      }
    }
    return points.map((p, i) => ({
      ...p,
      x: axis === "percent" ? i : (i * maxKm) / 100,
    }));
  }
  const keys = selected.map((r) => r.date + " · " + r.id);
  return (
    <>
      <Panel
        title="Select 2–5 runs"
        sub="Search up to 100 matching runs at a time, or add from Run Detail; selection stays while navigating"
      >
        <div className="analysis-controls">
          <input
            aria-label="Find comparison runs"
            placeholder="Find a run by name or date"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="text-button" onClick={() => setIds([])}>
            Clear selection
          </button>
        </div>
        <div className="comparison-picker">
          {runs
            .filter((r) =>
              (r.name + r.date).toLowerCase().includes(search.toLowerCase()),
            )
            .slice(0, 100)
            .map((r) => (
              <label key={r.id}>
                <input
                  type="checkbox"
                  checked={ids.includes(r.id)}
                  disabled={!ids.includes(r.id) && ids.length >= 5}
                  onChange={() =>
                    setIds(
                      ids.includes(r.id)
                        ? ids.filter((x) => x !== r.id)
                        : [...ids, r.id],
                    )
                  }
                />
                <span>
                  {r.date} · {r.name}
                  <small>
                    {fmt(r.distance / 1000)} km · {pace(r.pace)}/km ·{" "}
                    {r.classification?.label}
                  </small>
                </span>
              </label>
            ))}
        </div>
      </Panel>
      {selected.length < 2 ? (
        <p className="notice">
          Select at least two runs for direct comparison.
        </p>
      ) : (
        <>
          <Panel
            title="Run comparison"
            sub="Speed alone does not show aerobic improvement. Read HR, matched-band pace and drift alongside speed."
          >
            <div className="comparison-legend">
              {selected.map((r, i) => (
                <button
                  key={r.id}
                  onClick={() => open(r.id)}
                  style={{ borderColor: colors[i] }}
                >
                  <i style={{ background: colors[i] }} />
                  {r.date} · {r.name} →
                </button>
              ))}
            </div>
            <div className="table-scroll">
              <table
                className="comparison-table"
                style={{ minWidth: 190 + selected.length * 170 }}
              >
                <thead>
                  <tr>
                    <th>Metric</th>
                    {selected.map((r, i) => (
                      <th key={r.id} style={{ color: colors[i] }}>
                        {r.date}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Distance", (r: Point) => fmt(r.distance / 1000) + " km"],
                    [
                      "Elapsed / timer / moving",
                      (r: Point) =>
                        time(r.elapsed) +
                        " / " +
                        time(r.duration) +
                        " / " +
                        time(r.moving),
                    ],
                    ["Average pace", (r: Point) => pace(r.pace) + "/km"],
                    [
                      "Average / max HR",
                      (r: Point) => fmt(r.hr) + " / " + fmt(r.maxHR) + " bpm",
                    ],
                    ["Cadence", (r: Point) => fmt(r.cadence) + " spm"],
                    ["Elevation gain", (r: Point) => fmt(r.elevation) + " m"],
                    ["Calories", (r: Point) => fmt(r.calories)],
                    [
                      "Stride length",
                      (r: Point) =>
                        r.stride ? fmt(r.stride) + " cm" : "Unavailable",
                    ],
                    [
                      "Decoupling",
                      (r: Point) => fmt(r.metrics?.drift?.value) + "%",
                    ],
                    [
                      "First / second efficiency",
                      (r: Point) =>
                        fmt(r.metrics?.drift?.firstEfficiency, 4) +
                        " / " +
                        fmt(r.metrics?.drift?.secondEfficiency, 4),
                    ],
                    [
                      "HR change at matched pace",
                      (r: Point) =>
                        fmt(r.metrics?.drift?.hrAtPaceChange) + " bpm",
                    ],
                    [
                      "Pace change at matched HR",
                      (r: Point) =>
                        fmt(r.metrics?.drift?.paceAtHRChange) + " sec/km",
                    ],
                    [
                      "First / second half pace",
                      (r: Point) =>
                        pace(r.metrics?.drift?.firstPace) +
                        " / " +
                        pace(r.metrics?.drift?.secondPace),
                    ],
                    [
                      "Late split change",
                      (r: Point) => fmt(r.metrics?.splitChange) + "%",
                    ],
                    [
                      "Cadence change",
                      (r: Point) => fmt(r.metrics?.cadenceChange) + " spm",
                    ],
                    [
                      "Pace at 150–155 bpm",
                      (r: Point) => pace(r.bands?.hr?.["150"]?.value) + "/km",
                    ],
                    [
                      "Quality",
                      (r: Point) => r.quality?.issues?.join("; ") || "Usable",
                    ],
                  ].map(([label, f]: any) => (
                    <tr key={label}>
                      <th>{label}</th>
                      {selected.map((r) => (
                        <td key={r.id}>{f(r)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          {error && <p className="error">{error}</p>}
          <div className="analysis-controls">
            <label>
              Overlay axis
              <select
                aria-label="Comparison axis"
                value={axis}
                onChange={(e) => setAxis(e.target.value)}
              >
                <option value="percent">Percentage of elapsed activity</option>
                <option value="distance">Distance · km</option>
              </select>
            </label>
          </div>
          <div className="grid two">
            {["pace", "hr", "cadence", "elevation"].map((field) => (
              <Panel
                key={field}
                title={
                  field === "hr"
                    ? "Heart rate overlay"
                    : field[0].toUpperCase() + field.slice(1) + " overlay"
                }
                sub={
                  axis === "percent"
                    ? "0–100% of elapsed recording"
                    : "Distance · kilometres"
                }
              >
                <Plot
                  data={data(field)}
                  keys={keys}
                  x="x"
                  format={field === "pace" ? pace : undefined}
                />
              </Panel>
            ))}
            {["pace", "hr"].map((field) => {
              const m = new Map<number, Point>();
              selected.forEach((r, i) =>
                (r.metrics?.splits || []).forEach((s: Point) => {
                  const p = m.get(s.km) || { km: s.km };
                  p[keys[i]] = s[field];
                  m.set(s.km, p);
                }),
              );
              return (
                <Panel
                  key={field + "split"}
                  title={
                    field === "pace" ? "Pace by kilometre" : "HR by kilometre"
                  }
                  sub="Full-kilometre splits"
                >
                  <Plot
                    data={[...m.values()].sort((a, b) => a.km - b.km)}
                    keys={keys}
                    x="km"
                    format={field === "pace" ? pace : undefined}
                  />
                </Panel>
              );
            })}
            <Panel
              title="HR vs pace"
              sub="Matched sensor points; colours follow the selection legend"
            >
              <div className="analysis-chart">
                <ResponsiveContainer>
                  <ScatterChart>
                    <CartesianGrid stroke="#29352d" />
                    <XAxis
                      dataKey="pace"
                      type="number"
                      name="Pace"
                      domain={["auto", "auto"]}
                      tickFormatter={pace}
                    />
                    <YAxis
                      dataKey="hr"
                      type="number"
                      name="HR"
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#19221c",
                        border: "1px solid #435044",
                      }}
                    />
                    {selected.map((r, i) => (
                      <Scatter
                        key={r.id}
                        name={r.date}
                        fill={colors[i]}
                        data={(details[r.id]?.series?.records || [])
                          .filter(
                            (p: Point, j: number) =>
                              j % 10 === 0 &&
                              p.hr >= 35 &&
                              p.hr <= 220 &&
                              p.speed >= 0.5 &&
                              p.speed <= 10,
                          )
                          .map((p: Point) => ({
                            pace: 1000 / p.speed,
                            hr: p.hr,
                          }))}
                        isAnimationActive={false}
                      />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
export function RecoveryOverlay({
  runs,
  days,
  training,
  open,
  filters,
}: {
  runs: Point[];
  days: Point[];
  training: Point;
  open: (s: string) => void;
  filters: string;
}) {
  const [metric, setMetric] = useState("hrv"),
    [against, setAgainst] = useState("performance"),
    [lag, setLag] = useState("1"),
    [overlay, setOverlay] = useState(["hrv", "rhr", "sleep"]);
  const [response, setResponse] = useState<Point>({
      points: [],
      association: { n: 0, r: null },
    }),
    [failure, setFailure] = useState("");
  useEffect(() => {
    let active = true;
    setFailure("");
    fetch(
      "/api/analysis?" +
        filters +
        "&metric=" +
        metric +
        "&against=" +
        against +
        "&lag=" +
        lag,
    )
      .then((r) => {
        if (!r.ok) throw Error("Could not read recovery analysis.");
        return r.json();
      })
      .then((d) => {
        if (active) setResponse(d.recovery);
      })
      .catch((e) => {
        if (active) setFailure(e.message);
      });
    return () => {
      active = false;
    };
  }, [filters, metric, against, lag]);
  const data: Point[] = response.points,
    paired = data.filter((p) => p.x != null && p[against] != null),
    corr = response.association.r;
  const choices = [
    ["hrv", "HRV · ms"],
    ["rhr", "Resting HR · bpm"],
    ["sleep", "Sleep · hours"],
    ["sleepScore", "Sleep score"],
    ["bodyBattery", "Body Battery"],
    ["stress", "Stress"],
    ["volume", "Rolling 7-day km"],
    ["previousTraining", "Previous-day km"],
  ];
  // Standardisation allows overlays without pretending units are equal; raw values remain available.
  const stats = Object.fromEntries(
    overlay.map((k) => {
      const a = data.filter((d) => typeof d[k] === "number").map((d) => d[k]);
      const m = mean(a);
      return [
        k,
        {
          mean: m,
          sd:
            m == null
              ? null
              : Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / a.length),
        },
      ];
    }),
  );
  const normalized = data.map((d) => {
    const p: Point = { date: d.date };
    for (const k of overlay) {
      const s = stats[k];
      p[k] = d[k] != null && s.sd ? (d[k] - s.mean!) / s.sd : null;
    }
    return p;
  });
  return (
    <>
      {failure && <p className="error">{failure}</p>}
      <Panel
        title="Recovery & training overlay"
        sub="Standard deviations from each selected metric’s mean within the filtered dates; raw values below"
      >
        <div className="overlay-options">
          {choices.map(([k, label]) => (
            <label key={k}>
              <input
                type="checkbox"
                checked={overlay.includes(k)}
                onChange={() =>
                  setOverlay(
                    overlay.includes(k)
                      ? overlay.filter((x) => x !== k)
                      : [...overlay, k],
                  )
                }
              />
              {label}
            </label>
          ))}
        </div>
        <Plot data={normalized} keys={overlay} />
        <p className="caption">
          Zero is each metric’s mean; +1 is one standard deviation above it.
          Missing values create gaps. Normalised lines compare timing, not
          physiological magnitude.
        </p>
      </Panel>
      <Panel
        title="Explore associations"
        sub="Running performance = HR at 5:30–5:45/km from stable paired samples"
      >
        <div className="analysis-controls">
          <label>
            Recovery metric
            <select
              aria-label="Recovery metric"
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
            >
              {choices.slice(0, 6).map(([k, l]) => (
                <option value={k} key={k}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Compare with
            <select
              aria-label="Recovery comparison"
              value={against}
              onChange={(e) => setAgainst(e.target.value)}
            >
              <option value="performance">
                Running performance · HR at pace
              </option>
              <option value="volume">Rolling 7-day volume</option>
            </select>
          </label>
          <label>
            Recovery measured
            <select
              aria-label="Recovery lag"
              value={lag}
              onChange={(e) => setLag(e.target.value)}
            >
              <option value="0">Same day</option>
              <option value="1">Previous day</option>
              <option value="2">Previous 2 days · two-day lag</option>
            </select>
          </label>
        </div>
        <div className="analysis-stats">
          <Stat
            label="Paired days"
            value={String(paired.length)}
            note={
              paired.length < 10
                ? "Low sample · no correlation reported"
                : "Repeated daily values are not independent"
            }
          />
          <Stat
            label="Pearson association"
            value={corr == null ? "Insufficient reliable data" : fmt(corr, 2)}
            note="Association does not imply causation"
          />
        </div>
        <Plot data={paired} keys={[against]} x="x" scatter />
        <p className="caption">
          Unadjusted exploratory Pearson correlation needs ≥10 paired days and
          variation in both metrics. Weather, terrain, training intensity,
          selection effects and repeated measurements can explain apparent
          relationships. A two-day lag uses the observation exactly two days
          earlier.
        </p>
      </Panel>
      <Panel
        title="Underlying daily observations"
        sub="Raw units · source-run links appear when qualifying running data exists"
      >
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  "Date",
                  "HRV",
                  "RHR",
                  "Sleep h",
                  "Score",
                  "Battery",
                  "Stress",
                  "Previous km",
                  "Rolling 7 km",
                  "HR at pace",
                ].map((k) => (
                  <th key={k}>{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data
                .slice()
                .reverse()
                .map((d) => (
                  <tr key={d.date} onClick={() => d.id && open(d.id)}>
                    <td>
                      {d.date}
                      {d.id ? " →" : ""}
                    </td>
                    {[
                      "hrv",
                      "rhr",
                      "sleep",
                      "sleepScore",
                      "bodyBattery",
                      "stress",
                      "previousTraining",
                      "volume",
                      "performance",
                    ].map((k) => (
                      <td key={k}>{fmt(d[k])}</td>
                    ))}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
export function Calendar({
  runs,
  open,
}: {
  runs: Point[];
  open: (s: string) => void;
}) {
  const [month, setMonth] = useState(() => localDate(new Date()).slice(0, 7)),
    [view, setView] = useState("month"),
    [offset, setOffset] = useState(0);
  const first = new Date(month + "-01T12:00:00");
  const begin = shift(
    localDate(first),
    -((first.getDay() + 6) % 7) + offset * 7,
  );
  const count = view === "week" ? 7 : 42;
  const days = Array.from({ length: count }, (_, i) => shift(begin, i));
  function move(n: number) {
    if (view === "week") {
      setOffset(offset + n);
      return;
    }
    const d = new Date(month + "-01T12:00:00");
    d.setMonth(d.getMonth() + n);
    setMonth(localDate(d).slice(0, 7));
    setOffset(0);
  }
  return (
    <Panel
      title="Training calendar"
      sub="Activity-local dates · Monday-start weeks · calendar navigates all imported history"
    >
      <div className="analysis-controls calendar-controls">
        <button
          className="button"
          aria-label="Previous calendar period"
          onClick={() => move(-1)}
        >
          ←
        </button>
        <strong>{view === "week" ? begin : month}</strong>
        <button
          className="button"
          aria-label="Next calendar period"
          onClick={() => move(1)}
        >
          →
        </button>
        <select
          aria-label="Calendar view"
          value={view}
          onChange={(e) => {
            setView(e.target.value);
            setOffset(0);
          }}
        >
          <option value="month">Month</option>
          <option value="week">Week</option>
        </select>
        <input
          aria-label="Calendar month"
          type="month"
          value={month}
          onChange={(e) => {
            setMonth(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      <div className="calendar-head">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
      {Array.from({ length: count / 7 }, (_, w) => {
        const week = days.slice(w * 7, w * 7 + 7);
        const rs = runs.filter((r) => r.date >= week[0] && r.date <= week[6]);
        return (
          <div key={week[0]} className="calendar-week">
            <div className="calendar-grid">
              {week.map((d) => (
                <div
                  key={d}
                  className={
                    "calendar-day " + (d.slice(0, 7) !== month ? "outside" : "")
                  }
                >
                  <span className="calendar-date">{+d.slice(8)}</span>
                  {runs
                    .filter((r) => r.date === d)
                    .map((r) => (
                      <button
                        key={r.id}
                        className={
                          "calendar-run " +
                          ([
                            "Tempo",
                            "Threshold",
                            "Intervals",
                            "VO2 / high intensity",
                            "Race / time trial",
                          ].includes(r.classification?.label)
                            ? "intense"
                            : "")
                        }
                        onClick={() => open(r.id)}
                      >
                        <strong>{fmt(r.distance / 1000)} km</strong>
                        <span>{r.classification?.label || "Run"}</span>
                        <small>
                          {pace(r.pace)}/km · {fmt(r.hr)} bpm
                        </small>
                      </button>
                    ))}
                </div>
              ))}
            </div>
            <p className="calendar-total">
              Week of {week[0]}{" "}
              <strong>
                {fmt(rs.reduce((s, r) => s + (r.distance || 0), 0) / 1000)} km ·{" "}
                {rs.length} runs
              </strong>
            </p>
          </div>
        );
      })}
    </Panel>
  );
}

export function FitnessSnapshot({
  runs,
  allRuns,
  end,
  go,
}: {
  runs: Point[];
  allRuns: Point[];
  end: string;
  go: (s: string) => void;
}) {
  const choices = [140, 145, 150, 155, 160];
  const band = choices.sort(
    (a, b) =>
      bandPoints(runs, "hr", String(b)).reduce((s, p) => s + p.seconds, 0) -
      bandPoints(runs, "hr", String(a)).reduce((s, p) => s + p.seconds, 0),
  )[0];
  const aerobic = change(bandPoints(allRuns, "hr", String(band)), end, 28),
    inverse = change(bandPoints(allRuns, "pace", "330"), end, 28);
  const drift = [...runs]
    .reverse()
    .filter((r) => r.metrics?.drift?.value != null)
    .map((r) => ({ date: r.date, value: r.metrics.drift.value }));
  return (
    <Panel
      title="Fitness, from your running"
      sub="Observable changes · last 4 weeks versus previous 4"
    >
      <div className="fitness-links">
        <button onClick={() => go("Aerobic Efficiency")}>
          <span>
            Pace at {band}–{band + 5} bpm
            <small className="block">
              Most sampled aerobic band · {aerobic.a} recent / {aerobic.b}{" "}
              previous runs
            </small>
          </span>
          <strong>
            {aerobic.value == null
              ? "—"
              : `${aerobic.value > 0 ? "+" : ""}${fmt(aerobic.value)} sec/km`}{" "}
            →
          </strong>
        </button>
        <button onClick={() => go("HR at Pace")}>
          <span>
            HR at 5:30–5:45/km
            <small className="block">
              {inverse.a} recent / {inverse.b} previous runs
            </small>
          </span>
          <strong>
            {inverse.value == null
              ? "—"
              : `${inverse.value > 0 ? "+" : ""}${fmt(inverse.value)} bpm`}{" "}
            →
          </strong>
        </button>
        <button onClick={() => go("5K Performance")}>
          <span>Best 5 km in period</span>
          <strong>
            {time(
              Math.min(
                ...runs
                  .filter((r) => r.records?.["5 km"] && !r.records["5 km"].flag)
                  .map((r) => r.records["5 km"].seconds),
              ) || null,
            )}{" "}
            →
          </strong>
        </button>
      </div>
      <p className="caption">
        Longest run in selected period:{" "}
        {fmt(Math.max(0, ...runs.map((r) => (r.distance || 0) / 1000)))} km.
      </p>
      <p className="caption">
        Aerobic decoupling · lower generally means less late-run loss of speed
        per heartbeat.
      </p>
      <Plot data={drift} keys={["value"]} format={(v) => fmt(v) + "%"} />
      <button className="text-button" onClick={() => go("Fitness Trends")}>
        Explore all fitness components →
      </button>
    </Panel>
  );
}
