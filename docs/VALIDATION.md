# 5K evidence and turnaround fix · 26 October 2026

- All **86 Python tests pass**, including the original 53 and new 5K/evidence/import regression tests. Known examples cover continuous 5K, brief near-stop/U-turn patterns at 1 s and 5 s sampling, a fractional 3.2 s slowdown, isolated speed/cumulative-distance wobble, sustained stop, distance reset, GPS teleport, 11 s/48 s gaps, impossible pace, missing HR/cadence, credible reported PB without FIT, faster result selection, rounding corroboration, automatic evidence upgrade/deduplication and legacy-cache invalidation.
- FIT tests cover missing/empty/incomplete cache, nearly complete but short reported-5K streams, local-original reparse, failed-parse cooldown, explicit one-activity import, synthetic lockout, unchanged-healthy refresh reuse, Full History forcing, changed-summary downloads and preservation of a better cache/original after a bad response. Local revalidation keeps Host/Origin/custom-header checks and import locks.
- TypeScript checks and Vite production build pass; prebuilt assets are included. No production dependencies were added. Python compilation and all four unchanged `.command` launchers' Bash syntax checks pass. Full History intentionally passes the new force-revalidation flag through the existing Python entry point.
- Existing full-page, cross-navigation and interaction browser suites also passed on the updated production assets (empty and populated databases); the interaction test now waits for fixture loading before asserting refresh lockout.
- The production 5K page was checked at **1440px and 390px** against seven explicitly synthetic activities across all three evidence tiers. The expected PB is **26:49 · Garmin reported**, beating a 29:52 sensor result. PB progression contains exactly 29:52, 29:30 and 26:49; flagged faster results remain excluded. There are exactly seven primary performance rows, with no duplicate Garmin/FIT entries. Badges, diagnostics, missing metrics as `—`, record tiles, fitness/running trends and source-run navigation pass. Screenshots were visually reviewed; no document overflow, runtime/console errors or external browser requests were observed.
- Source/privacy regression: reviewed source and production assets; no real Garmin records, SQLite/DB files, FIT/GPS exports, credentials or JWTs were added. The official Garmin adapter, credential handling, `.gitignore`, launchers and production dependency declarations are unchanged. Temporary original downloads retain a `.zip` suffix covered by existing ignore protections. No live Garmin requests or personal data were used.
- Analysis fingerprint version **7** automatically recalculates existing activities. SQLite schema stays at version 2; existing records and keys are preserved. Reopening alone updates PB eligibility for already-imported Garmin split values. Normal Refresh retries incomplete FIT data on cooldown; Run Detail → **Revalidate activity data** forces an immediate single-activity download. Setup and Full History are not required for the corrected PB logic.

Methods, limits, retry lifecycle and Mac instructions are in `FIVE_K.md`. Actual device FIT sampling and original availability still require a local refresh on the user's Mac; Linux/synthetic validation does not exercise Finder/Gatekeeper or real Garmin authentication.

---

# Validation report · 25 October 2026

## Performance analytics update

- **53 Python tests passed**, including all pre-existing tests and new known-example tests for aerobic decoupling/components, warm-up/transient handling, pace-at-HR, HR-at-pace, missing HR/cadence, partial recordings, pauses, impossible distance increments, segment/record/PB progression, downhill flags, sampling precision, matching, classifications, rolling volume/rest days, abrupt changes, lagged recovery correlations and evidence-gated observations.
- **TypeScript checks and Vite production build passed.** Updated production assets are included; no Mac Node/npm dependency. Production package and Python requirement files are unchanged.
- **Browser QA passed on production assets at 1440×1000 and 390×1000:** Overview, Runs, Run Detail, Run Comparison, Aerobic Efficiency, HR at Pace, Fitness Trends, 5K Performance, Personal Records, Training Load, Recovery, Calendar, Observations and Settings. No document overflow, browser runtime/console errors or external browser requests were observed. Major feature screenshots were visually reviewed. Mobile history uses activity cards, comparison tables use internal scrolling/sticky metric labels, and long evidence tables are bounded. Additional wellness charts are expandable.
- **Interactions passed:** comparison selection capped at five, removal/clear, similar-pair addition, comparison legends → run, 5K chart point → run, record → run, calendar → run, band evidence → run, observation → supporting view, global filter persistence, activity search/distance filters, synthetic-refresh lockout, classification override/reset, calendar month/week controls, date periods, detail time/distance switching and synchronised hover tooltips.
- **Migration passed against an existing-style records/metadata database.** Sentinel metadata survives additive schema version 2; derived results reuse the cache and invalidate on changed sensor data. Local overrides are validated, parameterised and protected by the same Host/Origin/custom-header rules as refresh. Invalid analysis parameters are rejected.
- **Synthetic scale check:** 1,000 generated one-hour runs across approximately 5.5 years; first analysis 28.782 s, warm dashboard 0.112 s, JSON summary payload 4.67 MB. No high-frequency streams appear in the dashboard payload. These measurements describe this Linux test machine, not a performance guarantee on the Mac. First opening after upgrade may take longer while history is cached; subsequent work reuses derived data.
- **All four launchers pass Bash syntax checks**, retain executable mode 100755 and are unchanged. Existing setup/refresh/full-history/open Python entry points are retained. Garmin ingestion, official adapter, credential handling and production dependencies are unchanged.
- **Privacy regression passed:** reviewed current source and assets; no tracked SQLite/DB/FIT/GPS exports, credential/environment files or JWTs. Historical Git object names contain no local data/credential/export artifacts. New source uses invented fixtures only; benchmark databases and browser captures remain ignored/outside the repository. Compiled assets contain application code, not personal data. Existing ignore rules are preserved and extended for DB/GPS/network exports and credential backups. Browser requests are same-origin only, no telemetry or remote assets were introduced, and only the existing official read-only Garmin client handles Garmin access.

## Remaining local validation

No live Garmin API, key, athlete data or private database was accessed. After pulling, close/reopen using **Open Garmin Dashboard.command**, allow the automatic migration/cache build, and refresh normally. Setup does not need rerunning; keep the existing database and key. Check real FIT availability, original sampling/pauses/elevation, optional stride/elapsed fields, zone-based classifications and wellness coverage against your own recordings. Garmin does not certify inferred race intent, route equivalence or GPS accuracy; those limitations and unavailable data are visible in the app. Native macOS Finder/Gatekeeper behavior still needs the user's Mac.

Methods and exact thresholds are documented in `PERFORMANCE.md` and Data / Settings. Developer browser QA additionally uses `tests/browser_expanded.py` and `tests/browser_links.py`; Playwright/Chromium are development tools only.

---

# Previous validation · 24 October 2026

## Completed in Codex Cloud

- Production React/TypeScript build passed. Production CSS/JavaScript is checked into `companion/static/` and served by Python; Mac runtime needs no Node or npm.
- 24 Python unit/integration tests passed: transparent decoupling, missing HR, short/gapped streams, variable pace suppression, interpolated kilometre splits, documented health units, official response parsing, empty production database, date windows, range subdivision, incremental cursors, capped/repeated pagination, partial failures, incompatible schemas, forced token refresh with mocked HTTP 401, GPS projection and synthetic FIT/ZIP decoding.
- The local server passed loopback integration tests for static assets and APIs, no-data state, no GPS, cache-control/CSP, rejected hostile Host headers, cross-origin refresh requests, filesystem traversal and missing run IDs.
- Chromium inspected Overview, Runs, Running Trends, Recovery, Data / Settings at 1440×1000 desktop and 390×1000 mobile sizes, for both empty production-style and clearly labelled synthetic test databases. Run Detail was checked on both sizes with sensor charts and splits. No document-level overflow or browser/runtime errors were found. Wide run tables scroll inside their card on narrow screens.
- Screenshots of desktop overview, mobile run detail, trends, recovery and settings were visually reviewed. Empty production charts display unavailable data rather than synthetic or zero-filled history.
- Browser interaction checks passed: activity search, distance filters, global period selection, comparable-HR analysis on paired test FIT records, time/distance toggle and synchronised run-detail chart tooltips. No external browser requests were observed.
- `.command` launchers passed Bash syntax checks and have executable bits set. Python sources compile. README covers Finder/Gatekeeper, Python prerequisites, hidden key entry and routine double-click refresh/open.
- Source packaging excludes all databases, caches, tokens, credentials, environment files, original FIT files, Node dependencies and Python virtual environments. Compiled frontend assets contain application code only. Synthetic fixture generators are source-only, isolated under `tests/`, never imported during production startup. A marked synthetic database cannot sync from Garmin.

## Not verified / first Mac run required

No real Garmin API calls were made for this local architecture, and no personal fitness/health data was fetched or included. The previous cloud connection was blocked by Garmin's Cloudflare security service. The following remain unverified until a local Mac sync:

- Whether Garmin accepts the key and this Mac's network.
- Actual account-specific payloads, dataset permissions and device coverage.
- Which historical dates Garmin makes available and how much history imports.
- Original FIT variations from this user's devices (the decoder passed generated synthetic FIT/ZIP tests).
- Native Finder, Terminal, Python installation and Gatekeeper behavior on the user's macOS version. Shell syntax was tested on Linux, not macOS hardware.

`lastSuccess` means a refresh with no dataset warnings; `lastCompleted` can include partial datasets. Checked endpoints may legitimately contain no records. Some cached datasets are not dedicated UI visualizations; see ARCHITECTURE.md. No Training Readiness score, Training Status reconstruction, medical conclusions or precise GPS maps are generated.

## Reproduce

From the repository, build with `npm ci && npm run build`, install Python requirements, and run `python -m unittest discover -s tests -v`. Browser scripts `tests/browser_qa.py` and `tests/browser_interactions.py` expect empty and synthetic local test servers at ports 8765 and 8766 and a development Chromium at `/usr/bin/chromium`. They require Playwright only for developer QA, not Mac use. Run them in a network-enabled local execution sandbox that permits loopback sockets. `browser_qa.py` screenshots go under ignored `cache/browser-qa/`.
