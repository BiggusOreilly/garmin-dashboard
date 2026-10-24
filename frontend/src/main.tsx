import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Clock,
  Database,
  Footprints,
  Heart,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  Moon,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ScatterChart,
  Scatter,
  ZAxis,
  Legend,
} from "recharts";
import "./style.css";
type Run = {
  id: string;
  name: string;
  date: string;
  type: string;
  distance: number | null;
  duration: number | null;
  moving: number | null;
  pace: number | null;
  hr: number | null;
  maxHR: number | null;
  cadence: number | null;
  elevation: number | null;
  calories: number | null;
  fiveK: number | null;
  zones: (number | null)[];
  trainingEffect: number | null;
  recoveryTime: number | null;
};
type Day = { date: string; [key: string]: number | string | null };
type Dashboard = {
  activities: Run[];
  health: Day[];
  meta: {
    lastSuccess: string | null;
    lastCompleted: string | null;
    lastAttempt: string | null;
    earliest: string | null;
    connection: { state: string; message?: string };
    datasets: Record<string, { state: string; checked: string }>;
    warnings: string[];
    activityCount: number;
    healthDays: number;
    synthetic: boolean;
    fitnessAge: number | null;
  };
  gpsEnabled: boolean;
};
type RecordPoint = {
  t: number;
  distance: number | null;
  speed: number | null;
  hr: number | null;
  cadence: number | null;
  elevation: number | null;
};
type Detail = {
  series: { records: RecordPoint[]; laps: unknown[] };
  analysis: {
    drift: {
      value: number | null;
      reason: string;
      hrChange?: number;
      paceChange?: number;
    };
    splits: { km: number; pace: number }[];
    splitCV: number | null;
    splitChange: number | null;
    cadenceChange: number | null;
  };
};
const ACCENT = "#bce68b",
  SECOND = "#7d9f92";
const n = (v: number | null | undefined, d = 0) =>
  v == null || !Number.isFinite(v)
    ? "—"
    : v.toLocaleString("en-AU", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
const pace = (v: number | null | undefined) =>
  v == null || v <= 0
    ? "—"
    : `${Math.floor(Math.round(v) / 60)}:${String(Math.round(v) % 60).padStart(2, "0")}`;
const duration = (v: number | null) =>
  v == null
    ? "—"
    : v >= 3600
      ? `${Math.floor(v / 3600)}h ${Math.floor((v % 3600) / 60)}m`
      : `${Math.floor(v / 60)}:${String(Math.round(v) % 60).padStart(2, "0")}`;
const mean = (xs: (number | null | undefined)[]) => {
  const a = xs.filter((v): v is number => v != null);
  return a.length ? a.reduce((a, b) => a + b, 0) / a.length : null;
};
const sum = (xs: (number | null | undefined)[]) =>
  xs.reduce<number>((a, b) => a + (b || 0), 0);
const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const dateObj = (d: string) => new Date(d + "T12:00:00");
const shift = (d: string, days: number) => {
  const x = dateObj(d);
  x.setDate(x.getDate() + days);
  return iso(x);
};
const shortDate = (d: string) =>
  dateObj(d).toLocaleDateString("en-AU", { day: "numeric", month: "short" });
const fullDate = (d: string) =>
  dateObj(d).toLocaleDateString("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
const week = (d: string) => {
  const x = dateObj(d);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return iso(x);
};
const isRun = (r: Run) => r.type.includes("running");
const fmtTime = (d: string | null) =>
  d
    ? new Date(d).toLocaleString("en-AU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Never";
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(path, options);
  const data = await r.json();
  if (!r.ok)
    throw new Error(data.error || "The local dashboard could not respond.");
  return data;
}
const periods = [
  ["28", "4 weeks"],
  ["84", "12 weeks"],
  ["183", "6 months"],
  ["365", "1 year"],
  ["all", "All time"],
];
function Pill({
  children,
  muted = false,
}: {
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <span className={"pill " + (muted ? "muted" : "")}>
      <i />
      {children}
    </span>
  );
}
function Card({
  title,
  sub,
  children,
  wide = false,
  action,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
  wide?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <section className={"card " + (wide ? "wide" : "")}>
      <div className="card-head">
        <div>
          <h3>{title}</h3>
          {sub && <p>{sub}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function Empty({
  text = "Not enough recorded data for this chart.",
}: {
  text?: string;
}) {
  return (
    <div className="chart-empty">
      <Activity size={24} />
      <span>{text}</span>
    </div>
  );
}
function Kpi({
  label,
  value,
  unit,
  foot,
  icon,
  trend,
}: {
  label: string;
  value: string;
  unit?: string;
  foot?: string;
  icon?: React.ReactNode;
  trend?: number | null;
}) {
  return (
    <div className="kpi">
      <div className="kpi-top">
        <span>{label}</span>
        {icon}
      </div>
      <div className="kpi-value">
        {value}
        <small>{unit}</small>
      </div>
      <div className="kpi-foot">
        {trend != null && (
          <span className="change">
            {trend >= 0 ? (
              <ArrowUpRight size={13} />
            ) : (
              <ArrowDownRight size={13} />
            )}{" "}
            {n(Math.abs(trend), 1)}%
          </span>
        )}
        {foot || "Unavailable until recorded"}
      </div>
    </div>
  );
}
function Chart({
  data,
  field,
  unit = "",
  kind = "line",
  height = 220,
  sync,
  format,
  secondary,
  x = "date",
}: {
  data: Record<string, unknown>[];
  field: string;
  unit?: string;
  kind?: "line" | "bar" | "area";
  height?: number;
  sync?: string;
  format?: (v: number) => string;
  secondary?: string;
  x?: string;
}) {
  const present = data.some((d) => d[field] != null);
  if (!present) return <Empty />;
  const formatValue = (v: unknown) =>
    typeof v === "number"
      ? (format
          ? format(v)
          : n(v, ["km", "h", "kg", "brpm"].includes(unit) ? 1 : 0)) +
        (unit ? " " + unit : "")
      : String(v ?? "—");
  const common = {
    data,
    margin: { top: 12, right: 15, bottom: 0, left: 0 },
    syncId: sync,
  };
  const inner = (
    <>
      <CartesianGrid stroke="#28312d" vertical={false} strokeDasharray="3 5" />
      <XAxis
        dataKey={x}
        type={x !== "date" && kind !== "bar" ? "number" : "category"}
        domain={["dataMin", "dataMax"]}
        minTickGap={35}
        tickLine={false}
        axisLine={false}
        tick={{ fill: "#829087", fontSize: 11 }}
        tickFormatter={(v) =>
          x === "date" ? shortDate(String(v)) : n(Number(v), 1)
        }
      />
      <YAxis
        width={44}
        tickLine={false}
        axisLine={false}
        tick={{ fill: "#829087", fontSize: 11 }}
        tickFormatter={(v) =>
          format
            ? format(Number(v))
            : n(Number(v), ["h", "kg"].includes(unit) ? 1 : 0)
        }
        domain={kind === "bar" ? [0, "auto"] : ["auto", "auto"]}
      />
      <Tooltip
        contentStyle={{
          background: "#1c2520",
          border: "1px solid #3d4a40",
          borderRadius: 10,
          fontSize: 12,
          color: "#edf2eb",
        }}
        itemStyle={{ color: ACCENT }}
        labelFormatter={(v) =>
          x === "date"
            ? shortDate(String(v))
            : String(v) + (x === "km" ? " km" : " min")
        }
        formatter={formatValue}
      />
      {secondary && <Legend />}
    </>
  );
  return (
    <div className="chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {kind === "bar" ? (
          <BarChart {...common}>
            {inner}
            <Bar
              dataKey={field}
              fill={ACCENT}
              radius={[3, 3, 0, 0]}
              maxBarSize={28}
              isAnimationActive={false}
            />
          </BarChart>
        ) : kind === "area" ? (
          <AreaChart {...common}>
            {inner}
            <defs>
              <linearGradient id={"fill-" + field} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={ACCENT} stopOpacity={0.2} />
                <stop offset="100%" stopColor={ACCENT} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              dataKey={field}
              type="monotone"
              stroke={ACCENT}
              strokeWidth={2}
              fill={"url(#fill-" + field + ")"}
              connectNulls={false}
              isAnimationActive={false}
            />
          </AreaChart>
        ) : (
          <LineChart {...common}>
            {inner}
            <Line
              dataKey={field}
              type="monotone"
              stroke={ACCENT}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            {secondary && (
              <Line
                dataKey={secondary}
                stroke={SECOND}
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            )}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
function ScatterPlot({
  data,
  x = "pace",
  y = "hr",
  xUnit = "min/km",
  yUnit = "bpm",
}: {
  data: Record<string, unknown>[];
  x?: string;
  y?: string;
  xUnit?: string;
  yUnit?: string;
}) {
  if (!data.some((d) => d[x] != null && d[y] != null)) return <Empty />;
  return (
    <div className="chart" style={{ height: 230 }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 25, left: 0 }}>
          <CartesianGrid stroke="#28312d" strokeDasharray="3 5" />
          <XAxis
            type="number"
            dataKey={x}
            name={x}
            domain={["auto", "auto"]}
            tickFormatter={(v) =>
              x === "pace" ? pace(Number(v)) : n(Number(v), 1)
            }
            tick={{ fill: "#829087", fontSize: 11 }}
            label={{
              value: xUnit,
              position: "insideBottom",
              offset: -15,
              fill: "#829087",
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey={y}
            name={y}
            unit={" " + yUnit}
            domain={["auto", "auto"]}
            tick={{ fill: "#829087", fontSize: 11 }}
            width={65}
          />
          <ZAxis range={[25, 25]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{
              background: "#1c2520",
              border: "1px solid #3d4a40",
              borderRadius: 10,
              color: "#edf2eb",
            }}
            formatter={(v, name) => [
              name === "pace" ? pace(Number(v)) : n(Number(v), 1),
              name,
            ]}
          />
          <Scatter
            data={data}
            fill={ACCENT}
            fillOpacity={0.7}
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
function App() {
  const [data, setData] = useState<Dashboard | null>(null),
    [error, setError] = useState(""),
    [page, setPage] = useState("Overview"),
    [period, setPeriod] = useState("84"),
    [customStart, setCustomStart] = useState(""),
    [customEnd, setCustomEnd] = useState(""),
    [mobile, setMobile] = useState(false),
    [selected, setSelected] = useState<Run | null>(null),
    [detail, setDetail] = useState<Detail | null>(null),
    [detailError, setDetailError] = useState(""),
    [query, setQuery] = useState(""),
    [minKm, setMinKm] = useState(""),
    [maxKm, setMaxKm] = useState(""),
    [refreshing, setRefreshing] = useState(false),
    [message, setMessage] = useState(""),
    [recoveryX, setRecoveryX] = useState("hrv");
  async function load() {
    try {
      setData(await request<Dashboard>("/api/dashboard"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    if (!refreshing) return;
    const id = setInterval(async () => {
      try {
        const s = await request<{ running: boolean; message: string }>(
          "/api/sync",
        );
        setMessage(s.message);
        if (!s.running) {
          setRefreshing(false);
          load();
        }
      } catch {
        setRefreshing(false);
        setMessage(
          "Connection lost. Reopen the dashboard to check refresh status.",
        );
      }
    }, 1500);
    return () => clearInterval(id);
  }, [refreshing]);
  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    setDetail(null);
    setDetailError("");
    let active = true;
    request<Detail>("/api/run/" + selected.id)
      .then((d) => {
        if (active) setDetail(d);
      })
      .catch((e) => {
        if (active) setDetailError(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  async function refresh() {
    try {
      await request("/api/refresh", {
        method: "POST",
        headers: { "X-Stride-Local": "1" },
      });
      setRefreshing(true);
      setMessage("Connecting to Garmin on this device…");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  const today = iso(new Date()),
    end = customEnd || today,
    start =
      customStart ||
      (period === "all" ? "1900-01-01" : shift(end, -Number(period) + 1));
  const allRuns = data?.activities.filter(isRun) || [],
    runs = allRuns.filter((r) => r.date >= start && r.date <= end),
    days = (data?.health || []).filter((d) => d.date >= start && d.date <= end);
  const totalDistance = sum(runs.map((r) => r.distance)) / 1000,
    totalDuration = sum(runs.map((r) => r.duration));
  const paceRuns = runs.filter(
      (r) => r.distance != null && r.distance > 0 && r.duration != null,
    ),
    paceDistance = sum(paceRuns.map((r) => r.distance)) / 1000,
    paceDuration = sum(paceRuns.map((r) => r.duration));
  const thisWeek = week(today),
    previousWeek = shift(thisWeek, -7);
  const distanceIn = (a: string, b: string) =>
    sum(
      allRuns.filter((r) => r.date >= a && r.date <= b).map((r) => r.distance),
    ) / 1000;
  const currentKm = distanceIn(thisWeek, today),
    previousKm = distanceIn(previousWeek, shift(thisWeek, -1));
  const weekly = useMemo(() => {
    if (!data?.meta.lastCompleted && !data?.meta.activityCount) return [];
    const m: Record<
      string,
      { date: string; distance: number; longest: number }
    > = {};
    let a = week(
      start === "1900-01-01" ? allRuns.at(-1)?.date || today : start,
    );
    let cap = 0;
    while (a <= end && cap++ < 3000) {
      m[a] = { date: a, distance: 0, longest: 0 };
      a = shift(a, 7);
    }
    for (const r of runs) {
      const w = week(r.date);
      if (m[w]) {
        m[w].distance += (r.distance || 0) / 1000;
        m[w].longest = Math.max(m[w].longest, (r.distance || 0) / 1000);
      }
    }
    return Object.values(m);
  }, [data, start, end]);
  const daily = useMemo(() => {
    if (
      !data?.meta.lastCompleted &&
      !data?.meta.activityCount &&
      !data?.health.length
    )
      return [];
    const first =
      start === "1900-01-01" ? allRuns.at(-1)?.date || today : start;
    const result: Record<string, unknown>[] = [];
    for (let d = first, i = 0; d <= end && i < 20000; d = shift(d, 1), i++) {
      const rs = runs.filter((r) => r.date === d);
      const h = days.find((x) => x.date === d) || {};
      result.push({
        ...h,
        date: d,
        km: sum(rs.map((r) => r.distance)) / 1000,
        pace: mean(rs.map((r) => r.pace)),
        hr: mean(rs.map((r) => r.hr)),
        rolling7: distanceIn(shift(d, -6), d),
        rolling28: distanceIn(shift(d, -27), d),
      });
    }
    return result;
  }, [data, start, end]);
  const monthly = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of runs) {
      const k = r.date.slice(0, 7) + "-01";
      m[k] = (m[k] || 0) + (r.distance || 0) / 1000;
    }
    return Object.entries(m)
      .sort()
      .map(([date, distance]) => ({ date, distance }));
  }, [data, start, end]);
  const filtered = runs.filter(
    (r) =>
      (r.name + " " + r.type).toLowerCase().includes(query.toLowerCase()) &&
      (!minKm || (r.distance != null && r.distance >= Number(minKm) * 1000)) &&
      (!maxKm || (r.distance != null && r.distance <= Number(maxKm) * 1000)),
  );
  const latestHealth = (key: string) => {
    const d = [...days].reverse().find((d) => typeof d[key] === "number");
    return { value: d ? Number(d[key]) : null, date: d?.date };
  };
  const latest = data?.activities.find((r) => r.date >= start && r.date <= end);
  const nav = [
    { name: "Overview", icon: LayoutDashboard },
    { name: "Runs", icon: Footprints },
    { name: "Running Trends", icon: TrendingUp },
    { name: "Recovery", icon: Heart },
    { name: "Data / Settings", icon: Settings2 },
  ];
  const change = previousKm ? 100 * (currentKm / previousKm - 1) : null;
  const openRun = (r: Run) => {
    setSelected(r);
    setPage("Run Detail");
    window.scrollTo(0, 0);
  };
  const go = (p: string) => {
    setPage(p);
    setMobile(false);
    setSelected(null);
    window.scrollTo(0, 0);
  };
  const chartRuns = [...runs].reverse().map((r) => ({ ...r }));
  const recoveryPoints = runs.map((r) => ({
    ...r,
    ...days.find((d) => d.date === r.date),
  }));
  function zoneRows() {
    return [1, 2, 3, 4, 5].map((z, i) => ({
      zone: "Z" + z,
      seconds: sum(runs.map((r) => r.zones[i])),
    }));
  }
  function runTable(list: Run[], compact = false) {
    return (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Activity</th>
              <th>Distance</th>
              <th>Time</th>
              <th>Pace</th>
              <th>Avg HR</th>
              {!compact && (
                <>
                  <th>Max HR</th>
                  <th>Cadence</th>
                  <th>Ascent</th>
                  <th>Energy</th>
                </>
              )}
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((r) => (
              <tr key={r.id} onClick={() => openRun(r)}>
                <td>
                  <button
                    className="run-name"
                    onClick={(e) => {
                      e.stopPropagation();
                      openRun(r);
                    }}
                  >
                    <span className="run-icon">
                      <Footprints size={17} />
                    </span>
                    <span>
                      <strong>{r.name}</strong>
                      <small>
                        {shortDate(r.date)} · {r.type.replaceAll("_", " ")}
                      </small>
                    </span>
                  </button>
                </td>
                <td>
                  {n(r.distance == null ? null : r.distance / 1000, 2)}{" "}
                  <small>km</small>
                </td>
                <td>{duration(r.duration)}</td>
                <td>
                  {pace(r.pace)} <small>/km</small>
                </td>
                <td>
                  {n(r.hr)} <small>bpm</small>
                </td>
                {!compact && (
                  <>
                    <td>{n(r.maxHR)}</td>
                    <td>
                      {n(r.cadence)} <small>spm</small>
                    </td>
                    <td>
                      {n(r.elevation)} <small>m</small>
                    </td>
                    <td>
                      {n(r.calories)} <small>kcal</small>
                    </td>
                  </>
                )}
                <td>
                  <ArrowRight size={15} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.length && <Empty text="No runs match these filters." />}
      </div>
    );
  }
  function zoneBars(zones: (number | null)[]) {
    const total = sum(zones);
    return total ? (
      <div className="zones">
        {zones.map((v, i) => (
          <div key={i} className="zone-row">
            <span>Zone {i + 1}</span>
            <div className="zone-track">
              <i
                style={{
                  width: ((v || 0) / total) * 100 + "%",
                  opacity: 1 - i * 0.13,
                }}
              />
            </div>
            <strong>{n(((v || 0) / total) * 100)}%</strong>
            <small>{duration(v)}</small>
          </div>
        ))}
        <p className="caption">
          Recorded time in Garmin’s configured heart-rate zones.
        </p>
      </div>
    ) : (
      <Empty text="Recorded heart-rate-zone durations are unavailable." />
    );
  }
  return (
    <div className="app">
      <aside className={mobile ? "sidebar visible" : "sidebar"}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            go("Overview");
          }}
        >
          <div className="brand-mark">∧</div>stride<span>PERSONAL</span>
        </a>
        <div className="workspace">
          <span className="avatar">S</span>
          <div>
            My training space
            <small>
              <LockKeyhole size={10} /> Local & private
            </small>
          </div>
        </div>
        <p className="nav-label">YOUR DASHBOARD</p>
        <nav>
          {nav.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={
                page === name || (name === "Runs" && page === "Run Detail")
                  ? "active"
                  : ""
              }
              onClick={() => go(name)}
            >
              <Icon size={18} />
              {name}
              {name === "Runs" && (
                <span className="nav-count">{allRuns.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={21} />
          <strong>Your data. Your device.</strong>
          <p>
            Garmin data stays on this computer. No cloud uploads. No telemetry.
          </p>
          <div className="source">POWERED BY GARMIN DATA</div>
        </div>
      </aside>
      {mobile && <div className="scrim" onClick={() => setMobile(false)} />}
      <main>
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            aria-label="Open navigation"
            onClick={() => setMobile(!mobile)}
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumb">
            My training space <span>/</span>
            <strong>{page}</strong>
          </div>
          <div className="top-right">
            <Pill muted={!data?.meta.lastCompleted}>
              {data?.meta.lastCompleted
                ? "Local cache ready"
                : "Awaiting first import"}
            </Pill>
            <div className="top-avatar">S</div>
          </div>
        </header>
        <div className="content">
          {data?.meta.synthetic && (
            <div className="fixture-banner">
              SYNTHETIC TEST FIXTURE · Development only · These are not your
              Garmin metrics
            </div>
          )}
          <div className="page-heading">
            <div>
              <div className="eyebrow">PRIVATE TRAINING INTELLIGENCE</div>
              <h1>
                {page === "Overview"
                  ? "Every run. A clearer picture."
                  : page === "Run Detail"
                    ? selected?.name
                    : page === "Running Trends"
                      ? "Progress, in perspective."
                      : page === "Recovery"
                        ? "The other half of training."
                        : page === "Data / Settings"
                          ? "Your data, under your control."
                          : "Your running journal."}
              </h1>
              <p>
                {page === "Overview"
                  ? "Training and recovery, connected in one place."
                  : page === "Runs"
                    ? "Explore the details behind every kilometre."
                    : page === "Running Trends"
                      ? "See how your consistency, efficiency and volume evolve."
                      : page === "Recovery"
                        ? "Explore patterns across your training and daily recovery."
                        : page === "Run Detail" && selected
                          ? fullDate(selected.date)
                          : "A private, read-only connection to the official Garmin Personal API."}
              </p>
            </div>
            <button
              className="button refresh"
              disabled={refreshing || data?.meta.synthetic}
              onClick={refresh}
            >
              <RefreshCw size={15} className={refreshing ? "spin" : ""} />
              {refreshing ? "Refreshing…" : "Refresh data"}
            </button>
          </div>
          <div className="filter-bar">
            <div className="periods">
              {periods.map(([v, label]) => (
                <button
                  key={v}
                  className={
                    period === v && !customStart && !customEnd ? "selected" : ""
                  }
                  onClick={() => {
                    setPeriod(v);
                    setCustomStart("");
                    setCustomEnd("");
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="date-inputs">
              <input
                aria-label="Start date"
                type="date"
                value={customStart || (start === "1900-01-01" ? "" : start)}
                max={end}
                onChange={(e) => setCustomStart(e.target.value)}
              />
              <span>—</span>
              <input
                aria-label="End date"
                type="date"
                value={end}
                min={customStart}
                onChange={(e) => setCustomEnd(e.target.value)}
              />
            </div>
          </div>
          {message && (
            <div className="notice">
              <RefreshCw size={15} />
              {message}
              <button
                className="icon-button"
                onClick={() => setMessage("")}
                aria-label="Dismiss"
              >
                <X size={15} />
              </button>
            </div>
          )}
          {error && (
            <div className="error">
              <strong>Unable to load the dashboard.</strong> {error}{" "}
              <button onClick={load}>Try again</button>
            </div>
          )}
          {!data && !error && (
            <div className="loading">
              <RefreshCw className="spin" />
              Loading your local training space…
            </div>
          )}
          {data && page === "Overview" && (
            <>
              <div className="section-label">
                <span>TRAINING SNAPSHOT</span>
                <span>
                  {shortDate(
                    start === "1900-01-01"
                      ? data.meta.earliest || today
                      : start,
                  )}{" "}
                  — {shortDate(end)}
                </span>
              </div>
              <div className="kpi-grid">
                <Kpi
                  label="This week"
                  value={data.meta.lastCompleted ? n(currentKm, 1) : "—"}
                  unit="km"
                  foot={
                    data.meta.lastCompleted
                      ? `${n(previousKm, 1)} km previous week`
                      : "No runs imported yet"
                  }
                  trend={change}
                  icon={<Footprints size={16} />}
                />
                <Kpi
                  label="Rolling 7 days"
                  value={
                    data.meta.lastCompleted
                      ? n(distanceIn(shift(today, -6), today), 1)
                      : "—"
                  }
                  unit="km"
                  foot="Including today"
                  icon={<Activity size={16} />}
                />
                <Kpi
                  label="Rolling 28 days"
                  value={
                    data.meta.lastCompleted
                      ? n(distanceIn(shift(today, -27), today), 1)
                      : "—"
                  }
                  unit="km"
                  foot="Your recent training volume"
                  icon={<TrendingUp size={16} />}
                />
                <Kpi
                  label="Runs in period"
                  value={data.meta.lastCompleted ? n(runs.length) : "—"}
                  foot={
                    runs.length
                      ? `${n(totalDistance, 1)} km · ${duration(totalDuration)} total`
                      : "Your training story starts here"
                  }
                  icon={<Clock size={16} />}
                />
              </div>
              {!data.meta.activityCount && (
                <div className="onboarding">
                  <div className="onboard-symbol">
                    <Activity size={36} />
                  </div>
                  <div className="onboard-copy">
                    <span className="eyebrow">READY WHEN YOU ARE</span>
                    <h2>No Garmin data imported yet.</h2>
                    <p>
                      Your private training space is ready. Import your Garmin
                      history on your Mac to uncover the patterns behind your
                      running.
                    </p>
                    <div className="onboard-steps">
                      <span>
                        <b>1</b> Run Setup once
                      </span>
                      <span>
                        <b>2</b> Refresh Garmin Data
                      </span>
                      <span>
                        <b>3</b> Explore your training
                      </span>
                    </div>
                  </div>
                  <ShieldCheck className="onboard-shield" size={90} />
                </div>
              )}
              <div className="grid two">
                <Card
                  title="Weekly running volume"
                  sub="Kilometres per week · Monday to Sunday"
                  action={
                    <span className="chart-key">
                      <i /> Distance
                    </span>
                  }
                >
                  <Chart data={weekly} field="distance" unit="km" kind="bar" />
                </Card>
                <Card
                  title="Pace & heart rate"
                  sub="Each point is one run · timer-duration pace"
                  action={<span className="small-tag">EFFICIENCY</span>}
                >
                  <ScatterPlot data={chartRuns} />
                </Card>
              </div>
              <div className="grid two">
                <Card
                  title="Recent pace trend"
                  sub="Each run in the selected period · timer-duration pace"
                >
                  <Chart
                    data={chartRuns}
                    field="pace"
                    format={pace}
                    unit="/km"
                  />
                </Card>
                <Card
                  title="Recent heart-rate trend"
                  sub="Recorded average heart rate per run"
                >
                  <Chart data={chartRuns} field="hr" unit="bpm" />
                </Card>
              </div>
              <div className="section-label">
                <span>RECOVERY AT A GLANCE</span>
                <button onClick={() => go("Recovery")}>
                  Explore recovery <ArrowRight size={13} />
                </button>
              </div>
              <div className="kpi-grid recovery-kpis">
                {[
                  ["rhr", "Resting heart rate", "bpm", Heart],
                  ["hrv", "Overnight HRV", "ms", Activity],
                  ["sleep", "Sleep duration", "h", Moon],
                  ["bodyBattery", "Body Battery", "/100", Zap],
                ].map(([key, label, unit, Icon]) => {
                  const h = latestHealth(String(key));
                  const I = Icon as typeof Heart;
                  return (
                    <Kpi
                      key={String(key)}
                      label={String(label)}
                      value={n(
                        h.value == null
                          ? null
                          : key === "sleep"
                            ? h.value / 3600
                            : h.value,
                        key === "sleep" ? 1 : 0,
                      )}
                      unit={String(unit)}
                      foot={
                        h.date
                          ? `Last recorded ${shortDate(h.date)}`
                          : "Not yet recorded or imported"
                      }
                      icon={<I size={16} />}
                    />
                  );
                })}
              </div>
              <div className="grid overview-bottom">
                <Card
                  title="Recent runs"
                  sub="Your latest sessions in this period"
                  action={
                    <button className="text-button" onClick={() => go("Runs")}>
                      View all <ArrowRight size={13} />
                    </button>
                  }
                >
                  {runTable(runs.slice(0, 5), true)}
                </Card>
                <Card
                  title="Latest activity"
                  sub={
                    latest
                      ? shortDate(latest.date)
                      : "Your next insight starts with a run"
                  }
                >
                  {latest ? (
                    <div className="latest">
                      <div className="latest-icon">
                        <Footprints size={24} />
                      </div>
                      <h2>{latest.name}</h2>
                      <div className="latest-distance">
                        {n(
                          latest.distance == null
                            ? null
                            : latest.distance / 1000,
                          2,
                        )}
                        <small>km</small>
                      </div>
                      <div className="latest-stats">
                        <span>
                          {duration(latest.duration)}
                          <small>Time</small>
                        </span>
                        <span>
                          {pace(latest.pace)}
                          <small>min/km</small>
                        </span>
                        <span>
                          {n(latest.hr)}
                          <small>bpm</small>
                        </span>
                      </div>
                      <button
                        className="button"
                        onClick={() => openRun(latest)}
                      >
                        Explore run <ArrowRight size={15} />
                      </button>
                    </div>
                  ) : (
                    <div className="latest empty-latest">
                      <Footprints size={30} />
                      <h3>
                        A little more context,
                        <br />
                        with every kilometre.
                      </h3>
                      <p>
                        Splits, heart rate, cadence and effort will appear here
                        after your first import.
                      </p>
                    </div>
                  )}
                </Card>
              </div>
            </>
          )}
          {data && page === "Runs" && (
            <>
              <div className="run-filters">
                <div className="search">
                  <Search size={16} />
                  <input
                    placeholder="Search your runs…"
                    aria-label="Search runs"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
                <div className="distance-filter">
                  <span>Distance</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="Min km"
                    aria-label="Minimum distance kilometres"
                    value={minKm}
                    onChange={(e) => setMinKm(e.target.value)}
                  />
                  <span>–</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="Max km"
                    aria-label="Maximum distance kilometres"
                    value={maxKm}
                    onChange={(e) => setMaxKm(e.target.value)}
                  />
                </div>
                <span className="muted-text">{filtered.length} runs</span>
              </div>
              <Card
                title="Run history"
                sub="Select a run to explore its recorded details"
              >
                {runTable(filtered)}
              </Card>
            </>
          )}
          {data && page === "Running Trends" && (
            <>
              <div className="kpi-grid">
                <Kpi
                  label="Distance in period"
                  value={n(totalDistance, 1)}
                  unit="km"
                  foot={`${runs.length} recorded runs`}
                />
                <Kpi
                  label="Average pace"
                  value={pace(
                    paceDistance ? paceDuration / paceDistance : null,
                  )}
                  unit="/km"
                  foot="Distance-weighted · timer duration"
                />
                <Kpi
                  label="Longest run"
                  value={
                    runs.some((r) => r.distance != null)
                      ? n(
                          Math.max(...runs.map((r) => r.distance || 0)) / 1000,
                          2,
                        )
                      : "—"
                  }
                  unit="km"
                  foot="Within selected period"
                />
                <Kpi
                  label="Recorded 5 km best"
                  value={
                    runs.some((r) => r.fiveK != null)
                      ? duration(
                          Math.min(
                            ...runs
                              .filter((r) => r.fiveK != null)
                              .map((r) => r.fiveK!),
                          ),
                        )
                      : "—"
                  }
                  foot="Garmin fastest 5 km segment · selected period"
                />
              </div>
              <div className="grid two">
                <Card
                  title="Weekly kilometres"
                  sub="Volume progression · includes incomplete current week"
                >
                  <Chart data={weekly} field="distance" kind="bar" unit="km" />
                </Card>
                <Card
                  title="Rolling training volume"
                  sub="Daily trailing distance"
                >
                  <Chart
                    data={daily}
                    field="rolling7"
                    secondary="rolling28"
                    unit="km"
                  />
                </Card>
                <Card
                  title="Monthly distance"
                  sub="Calendar months · filtered dates"
                >
                  <Chart data={monthly} field="distance" kind="bar" unit="km" />
                </Card>
                <Card title="Average pace" sub="Each run · timer-duration pace">
                  <Chart
                    data={chartRuns}
                    field="pace"
                    format={pace}
                    unit="/km"
                  />
                </Card>
                <Card
                  title="Pace at comparable heart rates"
                  sub="Choose a fixed HR band · only recorded paired FIT samples"
                >
                  <Comparable runs={runs} mode="hr" />
                </Card>
                <Card
                  title="Heart rate at comparable paces"
                  sub="Choose a fixed pace band · only recorded paired FIT samples"
                >
                  <Comparable runs={runs} mode="pace" />
                </Card>
                <Card title="Average heart rate" sub="Per-run summary · bpm">
                  <Chart data={chartRuns} field="hr" unit="bpm" />
                </Card>
                <Card
                  title="Cadence trend"
                  sub="Average steps per minute · recorded values"
                >
                  <Chart data={chartRuns} field="cadence" unit="spm" />
                </Card>
                <Card
                  title="Longest run each week"
                  sub="A view of endurance volume"
                >
                  <Chart data={weekly} field="longest" kind="area" unit="km" />
                </Card>
                <Card
                  title="Recent 5 km performances"
                  sub="Garmin-reported fastest continuous 5 km segment, not an estimated race result"
                >
                  <Chart
                    data={chartRuns}
                    field="fiveK"
                    format={(v) => duration(v)}
                  />
                </Card>
                <Card
                  title="Intensity distribution"
                  sub="Measured time in Garmin’s heart-rate zones"
                >
                  {zoneBars(
                    [0, 1, 2, 3, 4].map((i) =>
                      sum(runs.map((r) => r.zones[i])),
                    ),
                  )}
                </Card>
                <Card title="Elevation gain" sub="Total ascent per run">
                  <Chart
                    data={chartRuns}
                    field="elevation"
                    unit="m"
                    kind="bar"
                  />
                </Card>
                <Card
                  title="Week-over-week volume change"
                  sub="Relative to previous calendar week · no percentage when previous week is zero"
                >
                  <Chart
                    data={weekly.map((w, i) => ({
                      ...w,
                      change:
                        i && weekly[i - 1].distance
                          ? 100 * (w.distance / weekly[i - 1].distance - 1)
                          : null,
                    }))}
                    field="change"
                    unit="%"
                    kind="bar"
                  />
                </Card>
              </div>
              <div className="method-note">
                <ShieldCheck size={18} />
                <p>
                  Training metrics describe recorded activity. Volume changes
                  are not injury-risk predictions. Missing sensor data stays
                  unavailable.
                </p>
              </div>
            </>
          )}
          {data && page === "Recovery" && (
            <>
              <div className="notice quiet">
                <Heart size={17} />
                Patterns are for exploration. Correlation does not establish
                causation, and these charts do not provide medical diagnoses.
              </div>
              <div className="grid two">
                {[
                  ["hrv", "Overnight HRV", "ms"],
                  ["rhr", "Resting heart rate", "bpm"],
                  ["sleep", "Sleep duration", "h"],
                  ["sleepScore", "Sleep score", "/100"],
                  ["bodyBattery", "Body Battery", "/100"],
                  ["stress", "Average stress", "/100"],
                  ["steps", "Daily steps", "steps"],
                  ["weight", "Body weight", "kg"],
                  ["bodyFat", "Body fat", "%"],
                  ["bmi", "BMI", ""],
                  ["respiration", "Respiration", "brpm"],
                  ["spo2", "Pulse Ox", "%"],
                  ["hydration", "Hydration", "ml"],
                ].map(([key, label, unit]) => (
                  <Card
                    key={key}
                    title={label}
                    sub="Daily recorded values · gaps indicate missing data"
                  >
                    <Chart
                      data={days.map((d) => ({
                        ...d,
                        [key]:
                          key === "sleep" && typeof d[key] === "number"
                            ? Number(d[key]) / 3600
                            : d[key],
                      }))}
                      field={key}
                      unit={unit}
                      sync="recovery"
                    />
                  </Card>
                ))}
                <Card
                  title="Recovery & running performance"
                  sub="Same-day daily values compared with each run’s pace"
                  action={
                    <select
                      aria-label="Recovery variable"
                      value={recoveryX}
                      onChange={(e) => setRecoveryX(e.target.value)}
                    >
                      {[
                        ["hrv", "HRV"],
                        ["rhr", "Resting HR"],
                        ["sleep", "Sleep (seconds)"],
                        ["bodyBattery", "Body Battery"],
                        ["stress", "Stress"],
                      ].map(([v, l]) => (
                        <option key={v} value={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  }
                >
                  <ScatterPlot
                    data={recoveryPoints}
                    x={recoveryX}
                    y="pace"
                    xUnit={recoveryX}
                    yUnit="sec/km"
                  />
                </Card>
                <Card
                  title="Running volume alongside recovery"
                  sub="Use synchronised hover to compare the same date"
                >
                  <Chart
                    data={daily}
                    field="km"
                    kind="bar"
                    unit="km"
                    sync="recovery"
                  />
                </Card>
              </div>
            </>
          )}
          {data && page === "Run Detail" && selected && (
            <>
              <button className="text-button back" onClick={() => go("Runs")}>
                <ArrowLeft size={15} />
                Back to runs
              </button>
              <div className="kpi-grid six">
                <Kpi
                  label="Distance"
                  value={n(
                    selected.distance == null ? null : selected.distance / 1000,
                    2,
                  )}
                  unit="km"
                  foot="Recorded distance"
                />
                <Kpi
                  label="Time"
                  value={duration(selected.duration)}
                  foot={`Moving ${duration(selected.moving)}`}
                />
                <Kpi
                  label="Average pace"
                  value={pace(selected.pace)}
                  unit="/km"
                  foot="Timer duration ÷ distance"
                />
                <Kpi
                  label="Average / max HR"
                  value={n(selected.hr)}
                  unit="bpm"
                  foot={`Maximum ${n(selected.maxHR)} bpm`}
                />
                <Kpi
                  label="Cadence"
                  value={n(selected.cadence)}
                  unit="spm"
                  foot="Recorded average"
                />
                <Kpi
                  label="Elevation gain"
                  value={n(selected.elevation)}
                  unit="m"
                  foot={`${n(selected.calories)} kcal`}
                />
              </div>
              {detailError && <div className="error">{detailError}</div>}
              {!detail && !detailError && (
                <div className="loading">
                  <RefreshCw className="spin" />
                  Reading local run details…
                </div>
              )}
              {detail && (
                <RunDetail detail={detail} run={selected} zoneBars={zoneBars} />
              )}
              <div className="method-note">
                <LockKeyhole size={18} />
                <p>
                  Precise GPS maps are disabled. Original FIT files may contain
                  routes, but coordinates are excluded from dashboard responses.
                </p>
              </div>
            </>
          )}
          {data && page === "Data / Settings" && (
            <>
              <div className="grid two">
                <Card
                  title="Local data library"
                  sub="Only this computer stores your Garmin records"
                >
                  <dl className="settings-list">
                    <dt>Last fully successful refresh</dt>
                    <dd>{fmtTime(data.meta.lastSuccess)}</dd>
                    <dt>Last completed attempt</dt>
                    <dd>{fmtTime(data.meta.lastCompleted)}</dd>
                    <dt>Earliest requested health date</dt>
                    <dd>{data.meta.earliest || "No import yet"}</dd>
                    <dt>Activities cached</dt>
                    <dd>{n(data.meta.activityCount)}</dd>
                    <dt>Health-summary days</dt>
                    <dd>{n(data.meta.healthDays)}</dd>
                    <dt>Fitness age (Garmin)</dt>
                    <dd>{n(data.meta.fitnessAge, 1)} years</dd>
                    <dt>API connection</dt>
                    <dd>{data.meta.connection.state.replaceAll("_", " ")}</dd>
                  </dl>
                  {data.meta.connection.message && (
                    <p className="error-text">{data.meta.connection.message}</p>
                  )}
                </Card>
                <Card title="Privacy & preferences" sub="Private by design">
                  <dl className="settings-list">
                    <dt>Units</dt>
                    <dd>km · m · kg · min/km</dd>
                    <dt>Precise routes / GPS</dt>
                    <dd>
                      <span className="small-tag">OFF</span>
                    </dd>
                    <dt>Garmin access</dt>
                    <dd>Read-only</dd>
                    <dt>Cloud uploads</dt>
                    <dd>Disabled</dd>
                    <dt>Analytics / telemetry</dt>
                    <dd>None</dd>
                    <dt>Dashboard access</dt>
                    <dd>This computer only</dd>
                  </dl>
                  <p className="caption">
                    Maps remain disabled in this release. Your browser never
                    receives your Garmin key or bearer token.
                  </p>
                </Card>
                <Card
                  title="Dataset availability"
                  sub="Checked means a request succeeded; devices and dates may still have no records"
                  wide
                >
                  <div className="dataset-grid">
                    {[
                      "daily",
                      "sleep",
                      "hrv",
                      "bodyBattery",
                      "stress",
                      "steps",
                      "hydration",
                      "weight",
                      "wellnessActivities",
                      "dailyHeartRate",
                      "spo2",
                      "zones",
                      "fitnessAge",
                    ].map((key) => (
                      <div className="dataset" key={key}>
                        <span>
                          {(
                            {
                              daily: "Daily summaries",
                              sleep: "Sleep",
                              hrv: "HRV",
                              bodyBattery: "Body Battery",
                              dailyHeartRate: "Daily heart rate",
                              spo2: "Pulse Ox",
                              fitnessAge: "Fitness age",
                              wellnessActivities: "Wellness activities",
                            } as Record<string, string>
                          )[key] || key[0].toUpperCase() + key.slice(1)}
                        </span>
                        <span
                          className={
                            data.meta.datasets[key]?.state === "checked"
                              ? "available"
                              : "muted-text"
                          }
                        >
                          {data.meta.datasets[key]?.state || "Not checked"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="caption">
                    Respiration, steps, hydration and Pulse Ox are also read
                    from daily summaries when present. Raw daily HR, FIT files
                    and additional fields remain in your local cache. Training
                    Readiness and Training Status have no dedicated endpoint in
                    the inspected Personal API schema; they are not invented.
                  </p>
                </Card>
                <Card
                  title="Import notes"
                  sub="Partial data never prevents you exploring successful imports"
                  wide
                >
                  {data.meta.warnings.length ? (
                    <ul className="warnings">
                      {data.meta.warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="settings-copy">
                      {data.meta.lastCompleted
                        ? "No dataset warnings in the last refresh."
                        : "No import has run yet. Double-click Refresh Garmin Data.command on your Mac."}
                    </p>
                  )}
                  <p className="caption">
                    Initial health history starts at your earliest recorded
                    activity, or one year back if there are none. Subsequent
                    refreshes revisit 14 days to catch recent edits; older
                    changes need an extended refresh. Original FIT files are
                    kept locally and may contain GPS. Back up your Mac securely.
                  </p>
                </Card>
                <Card
                  title="How the calculations work"
                  sub="Transparent methods, no invented recovery scores"
                  wide
                >
                  <div className="method-copy">
                    <p>
                      <strong>Average pace:</strong> total timer duration
                      divided by total recorded distance. Weekly distance uses
                      calendar weeks starting Monday in the activity’s local
                      date. Rolling windows include the selected day.
                    </p>
                    <p>
                      <strong>Aerobic decoupling:</strong> remove the first 10
                      minutes; divide the remaining elapsed time into equal
                      halves. Compute time-weighted mean speed divided by
                      time-weighted mean HR for each half. Report 100 × (first
                      ratio − second ratio) ÷ first ratio. Require ≥20 minutes
                      after warm-up, paired valid speed/HR coverage ≥80% in each
                      half, ≤10-second sample gaps, speed 0.5–10 m/s and HR
                      30–240 bpm. Suppress when speed coefficient of variation
                      exceeds 15%. Positive values mean lower speed per
                      heartbeat later; terrain, heat and sensors can affect the
                      result.
                    </p>
                    <p>
                      <strong>Splits:</strong> interpolate cumulative FIT
                      distance at each full kilometre. Split CV is standard
                      deviation ÷ mean full-kilometre time. Split change
                      compares the last half of full-kilometre splits to the
                      first half, omitting the middle split when odd. Positive
                      values mean slower later. This is a split-based
                      comparison, not a grade-adjusted race model.
                    </p>
                    <p>
                      <strong>Comparable HR / pace:</strong> time-weight
                      recorded FIT speed or HR only inside the selected fixed
                      band; require at least 120 seconds per run. No
                      summary-level matching or estimated sensor values. A
                      Garmin-reported fastest 5 km segment is shown only when
                      present; it is a best among imported records, not a
                      verified lifetime race PB.
                    </p>
                  </div>
                </Card>
              </div>
            </>
          )}
          <footer>
            <span>
              <LockKeyhole size={12} /> Stored locally. Built for the long run.
            </span>
            <span>
              Last refresh: {fmtTime(data?.meta.lastCompleted || null)}
              <i />
              Stride · Personal
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
function RunDetail({
  detail,
  run,
  zoneBars,
}: {
  detail: Detail;
  run: Run;
  zoneBars: (x: (number | null)[]) => React.ReactNode;
}) {
  const [axis, setAxis] = useState("time");
  const records = detail.series.records;
  const chart = records
    .filter((_, i) => i % Math.max(1, Math.floor(records.length / 1200)) === 0)
    .map((r) => ({
      ...r,
      minute: r.t / 60,
      km: r.distance == null ? null : r.distance / 1000,
      pace: r.speed && r.speed >= 0.5 ? 1000 / r.speed : null,
    }));
  const x = axis === "time" ? "minute" : "km",
    a = detail.analysis;
  return (
    <>
      <div className="detail-toolbar">
        <span className="muted-text">
          Recorded sensor streams · hover charts to compare
        </span>
        <div className="periods">
          <button
            className={axis === "time" ? "selected" : ""}
            onClick={() => setAxis("time")}
          >
            Time
          </button>
          <button
            className={axis === "distance" ? "selected" : ""}
            onClick={() => setAxis("distance")}
          >
            Distance
          </button>
        </div>
      </div>
      <div className="grid two">
        {[
          ["pace", "Pace", "min/km"],
          ["hr", "Heart rate", "bpm"],
          ["cadence", "Cadence", "spm"],
          ["elevation", "Elevation", "m"],
        ].map(([field, title, unit]) => (
          <Card
            title={title}
            sub={axis === "time" ? "Elapsed minutes" : "Distance · kilometres"}
            key={field}
          >
            <Chart
              data={chart}
              field={field}
              unit={unit}
              format={field === "pace" ? pace : undefined}
              x={x}
              sync="run"
            />
          </Card>
        ))}
        <Card
          title="Kilometre splits"
          sub="Full kilometres derived from recorded FIT distance"
        >
          <Chart
            data={a.splits}
            field="pace"
            kind="bar"
            x="km"
            format={pace}
            unit="/km"
          />
          {a.splits.length > 0 && (
            <div className="split-list">
              {a.splits.map((s) => (
                <div key={s.km}>
                  <span>{s.km} km</span>
                  <span>{pace(s.pace)} /km</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card
          title="Pace versus heart rate"
          sub="Paired sensor readings from this activity"
        >
          <ScatterPlot data={chart} />
        </Card>
        <Card title="Heart-rate zones" sub="Garmin-recorded zone durations">
          {zoneBars(run.zones)}
        </Card>
        <Card
          title="Run observations"
          sub="Derived only when the underlying records are sufficient"
        >
          <div className="observations">
            <div>
              <span>Aerobic decoupling</span>
              <strong>
                {n(a.drift.value, 1)}
                <small> %</small>
              </strong>
              <p>{a.drift.reason}</p>
            </div>
            <div>
              <span>Full-kilometre split consistency</span>
              <strong>
                {n(a.splitCV, 1)}
                <small> % CV</small>
              </strong>
              <p>Lower means more even full-kilometre times.</p>
            </div>
            <div>
              <span>Second-half split change</span>
              <strong>
                {n(a.splitChange, 1)}
                <small> %</small>
              </strong>
              <p>
                {a.splitChange == null
                  ? "More full-kilometre splits are needed."
                  : a.splitChange > 0
                    ? "Positive split: slower in the later full kilometres."
                    : "Negative split: faster in the later full kilometres."}
              </p>
            </div>
            <div>
              <span>Cadence change</span>
              <strong>
                {n(a.cadenceChange, 1)}
                <small> spm</small>
              </strong>
              <p>Second half minus first half of valid paired records.</p>
            </div>
            <div>
              <span>Late-run HR change after warm-up</span>
              <strong>
                {n(a.drift.hrChange, 1)}
                <small> %</small>
              </strong>
              <p>Only reported when decoupling quality checks pass.</p>
            </div>
            <div>
              <span>Late-run pace change after warm-up</span>
              <strong>
                {n(a.drift.paceChange, 1)}
                <small> %</small>
              </strong>
              <p>Positive means slower. See Data / Settings for the method.</p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
function Comparable({ runs, mode }: { runs: Run[]; mode: "hr" | "pace" }) {
  const [low, setLow] = useState(mode === "hr" ? 130 : 300),
    [high, setHigh] = useState(mode === "hr" ? 150 : 360),
    [points, setPoints] = useState<Record<string, unknown>[]>([]),
    [busy, setBusy] = useState(false),
    [failed, setFailed] = useState(false);
  async function calculate() {
    setBusy(true);
    setFailed(false);
    const out: Record<string, unknown>[] = [];
    try {
      for (const r of [...runs].reverse()) {
        const d = await request<Detail>("/api/run/" + r.id);
        let secs = 0,
          value = 0;
        const rs = d.series.records;
        for (let i = 1; i < rs.length; i++) {
          const b = rs[i],
            dt = b.t - rs[i - 1].t;
          if (
            dt <= 0 ||
            dt > 10 ||
            b.speed == null ||
            b.hr == null ||
            b.speed < 0.5 ||
            b.hr < 30 ||
            b.hr > 240
          )
            continue;
          const p = 1000 / b.speed;
          const match =
            mode === "hr" ? b.hr >= low && b.hr <= high : p >= low && p <= high;
          if (match) {
            secs += dt;
            value += (mode === "hr" ? b.speed : b.hr) * dt;
          }
        }
        if (secs >= 120)
          out.push({
            date: r.date,
            value: mode === "hr" ? 1000 / (value / secs) : value / secs,
          });
      }
      setPoints(out);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="band-filter">
        <input
          type="number"
          aria-label="Lower comparable band"
          value={low}
          onChange={(e) => {
            setLow(Number(e.target.value));
            setPoints([]);
          }}
        />
        <span>to</span>
        <input
          type="number"
          aria-label="Upper comparable band"
          value={high}
          onChange={(e) => {
            setHigh(Number(e.target.value));
            setPoints([]);
          }}
        />
        <span>{mode === "hr" ? "bpm" : "sec/km"}</span>
        <button
          className="button"
          onClick={calculate}
          disabled={busy || low > high}
        >
          {busy ? "Calculating…" : "Compare"}
        </button>
      </div>
      {failed ? (
        <Empty text="Could not read local records. Try Compare again." />
      ) : points.length ? (
        <Chart
          data={points}
          field="value"
          unit={mode === "hr" ? "/km" : "bpm"}
          format={mode === "hr" ? pace : undefined}
        />
      ) : (
        <Empty text="Select a band and compare runs with at least 2 minutes of matching sensor data." />
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
