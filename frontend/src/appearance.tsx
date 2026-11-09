import React, { useEffect, useState } from "react";
export const THEMES = {
  green: {
    accent: "#bce68b",
    soft: "#273322",
    bg: "#101512",
    surface: "#19201c",
    "series-2": "#94c9ed",
    "series-3": "#edc095",
    "series-4": "#c9b5f0",
    "series-5": "#efaeb5",
  },
  blue: {
    accent: "#92c9ff",
    soft: "#203247",
    bg: "#11151b",
    surface: "#1a2029",
    "series-2": "#bce68b",
    "series-3": "#edc095",
    "series-4": "#c9b5f0",
    "series-5": "#efaeb5",
  },
  orange: {
    accent: "#ffc18c",
    soft: "#3e2d20",
    bg: "#181411",
    surface: "#231e19",
    "series-2": "#94c9ed",
    "series-3": "#bce68b",
    "series-4": "#c9b5f0",
    "series-5": "#efaeb5",
  },
  purple: {
    accent: "#c8b0ff",
    soft: "#30263f",
    bg: "#15121a",
    surface: "#201b27",
    "series-2": "#bce68b",
    "series-3": "#edc095",
    "series-4": "#94c9ed",
    "series-5": "#efaeb5",
  },
  red: {
    accent: "#ffaaa9",
    soft: "#402626",
    bg: "#191212",
    surface: "#261c1d",
    "series-2": "#94c9ed",
    "series-3": "#bce68b",
    "series-4": "#edc095",
    "series-5": "#c9b5f0",
  },
};
export const colors = [
  "var(--accent)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
];
export const chartTokens = {
  text: "var(--text-muted)",
  grid: "var(--chart-grid)",
  tooltip: "var(--surface-raised)",
  border: "var(--border-strong)",
};
export function applyAppearance() {
  let theme = "green";
  try {
    theme = localStorage.getItem("stride-theme") || theme;
  } catch {}
  if (!(theme in THEMES)) theme = "green";
  const t = THEMES[theme as keyof typeof THEMES];
  document.documentElement.dataset.theme = theme;
  for (const [key, value] of Object.entries(t))
    document.documentElement.style.setProperty("--" + key, value);
  return theme;
}
export function useAppearance() {
  const [revision, setRevision] = useState(() => {
    applyAppearance();
    return 0;
  });
  useEffect(() => {
    applyAppearance();
    const update = () => {
      applyAppearance();
      setRevision((v) => v + 1);
    };
    window.addEventListener("stride-appearance", update);
    return () => window.removeEventListener("stride-appearance", update);
  }, []);
  return revision;
}
function save(k: string, v: string) {
  localStorage.setItem(k, v);
  window.dispatchEvent(new Event("stride-appearance"));
}
export function Appearance() {
  const [theme, setTheme] = useState(
      () => localStorage.getItem("stride-theme") || "green",
    ),
    [date, setDate] = useState(
      () => localStorage.getItem("stride-date-style") || "iso",
    );
  return (
    <section className="card analysis-panel appearance">
      <div className="card-head">
        <div>
          <h3>Appearance & preferences</h3>
          <p>
            Dark palettes with coordinated chart, navigation and control
            colours. Saved only in this browser.
          </p>
        </div>
      </div>
      <fieldset>
        <legend>Colour theme</legend>
        <div className="theme-options">
          {Object.entries(THEMES).map(([key, t]) => (
            <button
              key={key}
              aria-pressed={theme === key}
              onClick={() => {
                setTheme(key);
                save("stride-theme", key);
              }}
            >
              <i style={{ background: t.accent }} />
              {key[0].toUpperCase() + key.slice(1)}
            </button>
          ))}
        </div>
      </fieldset>
      <label>
        Date format
        <select
          aria-label="Date format"
          value={date}
          onChange={(e) => {
            setDate(e.target.value);
            save("stride-date-style", e.target.value);
          }}
        >
          <option value="iso">YYYY-MM-DD · 2026-11-05</option>
          <option value="long">D Month YYYY · 5 November 2026</option>
          <option value="short">D MMM YYYY · 5 Nov 2026</option>
        </select>
      </label>
      <p className="caption">
        Dates stay ISO internally. Native date inputs keep their normal browser
        behaviour. All analysis and observations remain local; no AI service or
        paid API is used.
      </p>
    </section>
  );
}
