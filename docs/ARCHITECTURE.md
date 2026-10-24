# Architecture and verified contract

This is a local-only application. There is no hosted data service, cloud dashboard runtime, analytics SDK, remote font, CDN dependency, or remote JavaScript. Codex compiles the React/TypeScript/Recharts frontend; Python serves those checked-in production assets without Node on the Mac.

- `companion/garmin.py`: adapter over Garmin's official `garmin_personal_api` package. The configured local key file is selected explicitly. Environment key discovery is deliberately not used in this architecture. Alternate API hosts are rejected. Only official client GET wrappers and the official token exchange are called. Raw HTTP bodies and exceptions never reach logs or users.
- `companion/ingest.py`: 99-record offset pagination until an empty page (does not assume a short page means EOF), deduplication, repeated-page detection, per-dataset cursors, 14-day overlap, bounded date windows and automatic subdivision of rejected ranges. Dates are local calendar dates. Two-day overlap for daily HR/SpO2. A failed window prevents that dataset's cursor advancing past the hole. Completed records are committed incrementally, so an interrupted first import resumes safely. A process lock prevents simultaneous launcher/browser imports.
- `companion/store.py`: SQLite with JSON payload records indexed by dataset and ID, fetched timestamps and separate import metadata. Missing optional fields remain null. Unknown fields are retained locally for future adapters. The directory is 0700 and files 0600. This is protected plaintext, not encrypted storage; use FileVault and encrypted backups.
- `companion/fit.py`: local FIT/ZIP reader using `fitdecode`, no browser automation. Original downloads are stored under ignored `data/fit/`; normalized time series never contain coordinates. FIT cadence is converted from strides/min to steps/min for running activities only. Garmin JSON cadence already in steps/min is not doubled.
- `companion/analysis.py`: explicitly projected frontend summaries, daily health normalization, full-kilometre splits and defensible decoupling. The UI documents formulas. Calculations run against the cache on request; no derived personal-data files enter source control.
- `companion/server.py`: binds only `127.0.0.1`; validates Host, Origin and cross-site fetch metadata; browser writes require a custom header. Only refresh is writable and Garmin itself remains read-only. No CORS, arbitrary file access or database download endpoint. No request logging. A restrictive CSP limits connections to the local application.

## Official sources inspected

- [Swagger reference](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/), inspected 24 October 2026; embedded OpenAPI 3.0.1, API version 1.0.0.
- [Authentication FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/).
- [Official Python library](https://github.com/garmin/connect-personal-api-python), release 1.0.0. Its real source interfaces `PersonalApiAuthenticator.obtain_token`, `resolve_api_key(key_file=...)`, `GarminPersonalApiClient`, `download_activity`, `search_activities`, and endpoint wrappers were inspected.

Official token responses are plain JWT text, not an assumed JSON object. The library handles this correctly and refreshes tokens with less than one hour remaining. This adapter checks before every request, and on a 401 forces one token replacement before retrying. 429 and selected 5xx errors receive bounded exponential backoff. No alternative host or private Connect endpoint is used.

## Endpoint coverage / limits

| Dataset | Official wrapper / endpoint | Request window |
| --- | --- | --- |
| Activities | `search_activities` / activitylist-service | 99 records per page |
| Activity details | `get_activity` / activity-service | Per activity |
| Original FIT | `download_activity` / download-service | Running activities only |
| Daily wellness | `get_daily_summaries` / usersummary-service/v2/dailysummaries | 28 days (official maximum one year) |
| Sleep | `get_daily_sleep_summaries` | 28 days (maximum 31) |
| HRV | `get_daily_hrv_summaries` | 28 days; subdivide if rejected |
| Body Battery | `get_daily_body_battery` | 28 days (maximum 31) |
| Steps / stress | `get_daily_steps` / `get_daily_stress` | 28 days (maximum 28) |
| Hydration | `get_daily_hydration` | 28 days (maximum 31) |
| Weight / body composition | `get_weight_measurements` | 28 days |
| Wellness activity summaries | `get_wellness_activity_summaries` | 28 days |
| Daily heart rate / SpO2 | `get_daily_heart_rate` / `get_daily_spo2` | One day |
| HR zone configuration | `get_heart_rate_zones` | Current configuration |
| Fitness age | `get_fitness_age` | Latest as of today |

The dashboard exposes useful daily-summary respiration, Pulse Ox, hydration and body-composition fields as recorded. Raw daily HR, Body Battery reports, stress/steps/hydration responses, wellness activity summaries, HR zone configuration, fitness-age response, activity detail split summaries and FIT lap records are cached locally. Some are source/cache data rather than dedicated visualizations in this release. The current Garmin fitness age is displayed only from the documented `fitnessAge` field; unknown or changed response shapes remain unavailable. Nutrition and reproductive-health endpoints are intentionally not imported for a running/recovery dashboard.

The inspected schema has no dedicated Training Readiness / Training Status endpoints. No proxy recovery score is created. Exact GPS mapping is not implemented. Run sensor charts use original FIT records when downloadable, not invented measurements from summary values. Missing or unsupported original formats leave sensor charts unavailable. Garmin `splitSummaries` can represent split categories rather than individual kilometre laps, so they are not relabelled as kilometre splits.

## History and edits

Initial activity pagination imports all available activities. Initial health starts on the earliest activity date, or one year ago for an account without activities. Each dataset resumes from its own cursor. Empty successful historical windows are recorded; failed or inaccessible dates become warnings. `lastSuccess` advances only with no warnings. `lastCompleted` records a completed attempt even with partial datasets. Null versus zero is preserved for sensor values.

Recent edits are revisited for 14 days (daily HR/SpO2: two days). Garmin's search is based on start date, not a documented updated-since cursor. Changes/deletions to older activities are not automatically detected. There is no claim of complete account mutation tracking. Use the extended-history launcher to revisit the full source history. Previously cached activities deleted at Garmin are retained locally; there is no automatic deletion propagation. This is documented rather than silently discarding local data.

## Validation boundary

Cloud tests use explicitly synthetic data under `/workspace/work/*test*`, outside the repository. Production startup does not load fixtures. Fixture databases are marked and their UI displays a persistent synthetic-data banner; refresh is disabled in both frontend and backend. No real Garmin authentication or live data was exercised for this architecture. Real FIT variations, account-specific schema differences, historic Garmin retention and macOS Finder/Gatekeeper behavior require the first Mac run.
