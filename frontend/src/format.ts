/** Presentation only: never round stored samples or inputs used by calculations. */
export const unavailable = "—";
export const finite = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);
export const formatNumber = (v: unknown, d = 0) =>
  finite(v)
    ? new Intl.NumberFormat("en-AU", { maximumFractionDigits: d }).format(
        Object.is(v, -0) ? 0 : v,
      )
    : unavailable;
export const withUnit = (v: unknown, unit: string, d = 0) =>
  finite(v)
    ? `${formatNumber(v, d)}${unit.startsWith("%") ? "" : " "}${unit}`
    : unavailable;
export function formatDuration(v: unknown) {
  if (!finite(v) || v < 0) return unavailable;
  const s = Math.round(v),
    h = Math.floor(s / 3600),
    m = Math.floor((s % 3600) / 60);
  return `${h ? h + "h " : ""}${m}m ${s % 60}s`;
}
export function formatPace(v: unknown) {
  if (!finite(v) || v <= 0) return unavailable;
  const s = Math.round(v);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
export const paceWithUnit = (v: unknown) =>
  finite(v) && v > 0 ? formatPace(v) + "/km" : unavailable;
export const formatHeartRate = (v: unknown) => withUnit(v, "bpm");
export const formatCadence = (v: unknown) => withUnit(v, "spm");
export const formatDistance = (metres: unknown, d = 2) =>
  finite(metres) ? withUnit(metres / 1000, "km", d) : unavailable;
export const formatPercent = (v: unknown) => withUnit(v, "%", 1);
export const formatElevation = (v: unknown) => withUnit(v, "m");
export const formatCalories = (v: unknown) => withUnit(v, "kcal");
export const formatDifference = (v: unknown, unit = "", d = 1) =>
  finite(v)
    ? ["sec", "s", "sec/km"].includes(unit)
      ? `${v > 0 ? "+" : v < 0 ? "−" : ""}${unit === "sec/km" ? formatNumber(Math.abs(v), 0) + " sec/km" : formatDuration(Math.abs(v))}`
      : `${v > 0 ? "+" : ""}${formatNumber(v, d)}${unit ? (unit.startsWith("%") ? "" : " ") + unit : ""}`
    : unavailable;
export type DateStyle = "iso" | "long" | "short";
export const readDateStyle = (): DateStyle => {
  try {
    const p = localStorage.getItem("stride-date-style");
    return p === "long" || p === "short" ? p : "iso";
  } catch {
    return "iso";
  }
};
export function formatDate(
  v: unknown,
  style: DateStyle | "compact" = readDateStyle(),
) {
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(v))
    return unavailable;
  const day = v.slice(0, 10),
    date = new Date(day + "T12:00:00Z");
  if (!Number.isFinite(date.getTime())) return unavailable;
  if (style === "iso") return day;
  return date.toLocaleDateString("en-AU", {
    timeZone: "UTC",
    day: "numeric",
    month: style === "long" ? "long" : "short",
    ...(style === "compact" ? {} : { year: "numeric" }),
  });
}
export function formatDateTime(v: unknown) {
  if (typeof v !== "string") return unavailable;
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return unavailable;
  const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return (
    formatDate(day) +
    " · " +
    d.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" })
  );
}
export function displayText(text: unknown) {
  return String(text ?? "")
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, (d) => formatDate(d))
    .replace(/\b(\d+\.\d+)\s?s\b/g, (_, n) => formatDuration(Number(n)))
    .replace(/\bcredible\s+/gi, "");
}
const labels: Record<string, string> = {
  percent: "Activity completed",
  hr: "Heart rate",
  maxHR: "Maximum heart rate",
  pace: "Pace",
  cadence: "Cadence",
  elevation: "Elevation",
  km: "Distance",
  distance: "Distance",
  zoneMinutes: "Intensity-weighted minutes",
  rolling7: "7-day rolling distance",
  rolling28: "28-day rolling distance",
  rolling: "28-day rolling mean",
  value: "Recorded value",
  result: "Performance",
  change: "Change",
  efficiency: "Speed per heartbeat",
  hrv: "HRV",
  rhr: "Resting heart rate",
  sleep: "Sleep duration",
  sleepScore: "Sleep score",
  bodyBattery: "Body Battery",
  stress: "Stress",
  previousTraining: "Previous-day distance",
  volume: "7-day rolling distance",
  performance: "HR at matched pace",
  minute: "Elapsed time",
  x: "Recovery metric",
  date: "Date",
  fiveKValue: "5K performance",
  fiveK: "5K performance",
  seconds: "Duration",
  t: "Elapsed time",
  splitCV: "Split variation",
  splitChange: "Late-run split change",
  cadenceChange: "Cadence change",
  longest: "Longest run",
  weight: "Weight",
  bodyFat: "Body fat",
  bmi: "BMI",
  steps: "Steps",
  respiration: "Respiration",
  spo2: "Pulse Ox",
  hydration: "Hydration",
  count: "Run count",
};
export const metricLabel = (k: string) =>
  labels[k] ||
  k.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^./, (c) => c.toUpperCase());
export function metricValue(k: string, v: unknown) {
  if (!finite(v)) return unavailable;
  if (["pace", "firstPace", "secondPace"].includes(k)) return paceWithUnit(v);
  if (
    [
      "result",
      "fiveK",
      "fiveKValue",
      "seconds",
      "duration",
      "moving",
      "elapsed",
      "t",
      "finalKmDuration",
    ].includes(k)
  )
    return formatDuration(v);
  if (k === "minute") return formatDuration(v * 60);
  if (["hr", "maxHR", "rhr", "performance", "hrChange"].includes(k))
    return formatHeartRate(v);
  if (k === "cadence" || k === "cadenceChange") return formatCadence(v);
  if (
    [
      "km",
      "distance",
      "rolling7",
      "rolling28",
      "longest",
      "volume",
      "previousTraining",
    ].includes(k)
  )
    return withUnit(v, "km", 1);
  if (k === "elevation") return formatElevation(v);
  if (["percent", "splitCV", "splitChange", "bodyFat", "spo2"].includes(k))
    return formatPercent(v);
  if (k === "zoneMinutes") return withUnit(v, "min", 1);
  if (k === "hrv") return withUnit(v, "ms");
  if (k === "sleep") return withUnit(v, "h", 1);
  if (k === "weight") return withUnit(v, "kg", 1);
  if (k === "efficiency") return formatNumber(v, 4);
  return formatNumber(v, 1);
}
export function orderRuns<
  T extends { date: string; start?: string | null; id: string },
>(runs: T[]) {
  return [...runs].sort(
    (a, b) =>
      (a.start || a.date).localeCompare(b.start || b.date) ||
      a.id.localeCompare(b.id, undefined, { numeric: true }),
  );
}
export function runLabels<
  T extends { date: string; start?: string | null; id: string; name?: string },
>(runs: T[]) {
  const labels: Record<string, string> = { percent: "Activity completed" };
  const used = new Map<string, number>();
  for (const r of orderRuns(runs)) {
    let label = formatDate(r.date);
    if (runs.filter((x) => x.date === r.date).length > 1) {
      const time = r.start?.match(/T(\d{2}:\d{2})/)?.[1];
      label +=
        " · " + (time || r.name?.replace(/\b\d{8,}\b/g, "").trim() || "Run");
      const n = used.get(label) || 0;
      used.set(label, n + 1);
      if (n) label += ` (${n + 1})`;
    }
    labels[r.id] = label;
  }
  return labels;
}
