# Stride refinement · 9 November 2026

This is an extension of the existing Python/SQLite/React application. It adds no AI integration, inference service, paid API, telemetry or production dependency. Existing observations remain deterministic and local.

## Presentation and preferences

`frontend/src/format.ts` is the shared presentation boundary. Durations round once to whole seconds and render `0m 42s`, `26m 49s`, `1h 4m 12s`. Pace stays `5:22/km`. Stored and calculated values retain full precision. Shared helpers cover numbers, missing values, differences, heart rate, cadence, distance, elevation, calories, percentages and dates. Unknown/non-finite values render `—`; unit helpers do not append units to missing values. Diagnostic sampling precision and time differences are bounded for display.

Settings → Appearance & preferences offers Green, Blue, Orange, Purple and Red dark palettes. Tokens coordinate the background, surfaces, accent, active controls, badges and charts. Each palette retains five distinct comparison colours. Text, grid, tooltip, dropdown and table colours use shared tokens. Unit checks require WCAG AA contrast (4.5:1) for normal/muted text against each theme surface and 3:1 for graphical series. Preferences are saved only in this browser's local storage.

Date options are ISO, long (5 November 2026), or short (5 Nov 2026). Tables, selected-run labels, tooltips, detail pages, calendar totals, record history and status times follow this preference. Compact chart axes can use shorter dates; tooltips show the selected full date. Database dates, parsing, filters and native date inputs remain ISO/native.

Comparison sorts a copy of selected activities by start timestamp, oldest first; date and stable ID provide fallback ties. Unique internal series keys are separate from display labels. A unique day shows just its date; same-day activities add local start time or a short distinguishing name. Legends, columns, curves and colours use that same order. IDs remain internal routing keys. Prominent 5K labels use plain performance terminology, retaining Sensor validated / Garmin reported / Flagged evidence.

## Personal records and exact 10K evidence

The official Garmin Personal API Swagger documentation was inspected on 9 November 2026. Its activity schema explicitly defines `fastestSplit_10000` as “the time, in seconds, for the fastest 10k meter split in the activity” (double). Source: https://developer.garmin.com/gc-developer-program/personal/swagger-docs/. The existing official client and cached activity adapter now project that field; no new endpoint or authentication method was introduced.

The previous search tolerated brief anomalies only for 5K. Version **8** applies bounded candidate-level tolerance to 1 km, 1 mile, 3 km, 5 km and 10 km. All elapsed slowdown time remains included. The current rules are:

- Total questionable duration is capped at `min(24 seconds, max(4 seconds, 12 × target metres / 5000), 1% of candidate elapsed time)`.
- Maximum consecutive questionable duration stays at 8 seconds.
- Separate questionable episodes are capped at `max(1, min(6, ceil(target metres / 2000)))`.
- Affected distance is capped at `max(10 metres, min(60 metres, 0.6% of target distance))`.
- Individual non-stationary speed/distance disagreement remains capped at 20 metres. Gaps over 10 seconds, cumulative resets, time reversal and implied teleports over 10 m/s remain rejected.
- Overall candidate speed above 7 m/s for distances ≥3 km (10 m/s for shorter distances) is excluded as implausible. The conservative 400 m precision/continuous-recording rules remain unchanged.

These are transparent quality tolerances, not guarantees of GPS correctness or physiological thresholds. No position or heading data is used. Distance is cumulative travelled distance; an incomplete stream is never extended to reach a target.

`recordPerformances` stores one best evidence-labelled result per activity/distance. Explicit Garmin-reported exact 10K results use the existing 5K hierarchy and can establish a PB when FIT is inconclusive. Matching results prefer sensor evidence without duplication; stronger contradictions remain flagged. PB comparisons keep underlying precision. A first valid result establishes the record; slower valid performances remain in the new performance history without becoming PB events.

Activities within 2% of a target distance without an exact result remain visible as **Recorded effort**, with actual summary distance/time as context and a specific explanation such as “10K recorded · exact 10,000 m split unavailable · FIT stream incomplete.” These are not timed personal records. A marginally short recording cannot become an invented exact 10K. The history links to Run Detail, where the existing **Revalidate activity data** action remains available. Near-distance and rejected runs retain diagnostics. The 10K detail panel also shows evidence and reason.

## More useful charts

The Overview pace/HR view distinguishes earlier and recent runs with detailed date/distance/pace/HR hover information. Existing global distance/classification filters apply. A toggle shows the observed pace-at-150–155-bpm timeline from the existing warm-up-excluded stable-sample analysis; a link opens the full matched-band analysis. Insufficient samples are labelled, with no fitted regression or invented fitness score.

Run Detail and Comparison use time-weighted 5 bpm bins (at least 30 seconds of valid paired data), plotting mean speed converted to pace against mean HR. Coverage and sample counts are shown. These within-run bins deliberately include warm-up; the separate aerobic-efficiency analysis retains its stricter warm-up exclusion and longer matching requirements. A Recorded samples toggle retains access to a bounded display of the original paired measurements (≤300 display points per run). Multi-run colours and labels follow chronological order. No causal, terrain-adjusted or statistically unsupported regression is claimed.

All chart tooltips and legends use human names and shared units/precision. Recovery overlays remain standardised values in SD, distinct from their raw-unit association plots. Additional wellness scatter plots convert sleep seconds to hours consistently. No new data service is used.

## Existing installation

There is **no SQL schema migration and no new production dependency**. SQLite remains schema version 2; the derived fingerprint changes from 7 to 8 and automatically recalculates existing cached activities. Records, original FIT files, credentials and local overrides remain intact. Node/npm is development-only; the built frontend is committed.

After merging/pulling:

1. Close the running dashboard launcher window.
2. Pull/download the complete update, including `companion/static/`, into the existing dashboard folder. Keep `data/` and the existing local key.
3. Double-click **Open Garmin Dashboard.command**. Allow the first analysis rebuild to finish.
4. Double-click **Refresh Garmin Data.command** normally for new/recent summaries and bounded retries of missing/incomplete FIT files.
5. If a specific record still has an incomplete FIT stream, open its activity and click **Revalidate activity data** to force that original's download/reparse. This is optional when cached data is already adequate.
6. Select your palette and date format in **Data / Settings → Appearance & preferences**.

Setup does not need rerunning. Full History is not needed for the new calculations or a recent 10K. It remains optional for revisiting old summaries/edits outside the normal refresh overlap. If an older cached activity lacks an exact Garmin split and no FIT segment is available, the app will explain that limitation; it cannot manufacture Garmin's missing historical field. Live FIT variation, actual split availability and native macOS execution still need validation on the Mac.
