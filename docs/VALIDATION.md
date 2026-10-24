# Validation report · 24 October 2026

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
