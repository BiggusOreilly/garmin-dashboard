# Stride · Your private Garmin dashboard

Stride connects your running and recovery in a polished, dark dashboard. Explore runs, kilometre splits, pace and heart rate, cadence, elevation, rolling volume, training trends, sleep, HRV, resting heart rate, stress and Body Battery where Garmin has recorded them.

**Your Mac downloads and stores your Garmin data. Nothing is uploaded to GitHub or another service.** The dashboard and Garmin connection run on your Mac, with no Node/npm requirement. There is no cloud-hosted personal-data dashboard.

## One-time Mac setup — no developer commands

1. Download this repository to your Mac and extract it into a normal local folder, such as `Documents/Garmin Dashboard`. Avoid iCloud Drive, Dropbox or another automatically synced folder if you want the downloaded data to stay only on this Mac.
2. Double-click **Setup Garmin Dashboard.command**. If macOS blocks a downloaded launcher, Control-click it and choose **Open**. On recent macOS versions, you may need **System Settings → Privacy & Security → Open Anyway** for a blocked file you trust. Do not disable Gatekeeper globally.
3. Setup checks for Python 3.12 or newer. If missing, it opens Python's official download page. Install the macOS universal installer, then double-click Setup again. Setup creates a private `.venv` folder and installs Garmin's official Python client and the FIT reader. You do not need to create an environment file or install Node.
4. When asked, paste your Garmin **Personal API key** and press Return. The text intentionally stays invisible. This is not your Garmin password. Obtain the key through Garmin Connect's Personal API settings if needed. Setup never puts it into a command or shell history.
5. Double-click **Refresh Garmin Data.command**. The initial history import can take time. Leave its window open until it reports completion. If there are partial datasets, Data / Settings explains them. You can safely run Refresh again after interruption.
6. Double-click **Open Garmin Dashboard.command**. It starts the local server automatically and opens your default browser. Keep that launcher window open while using the dashboard. Closing it stops the server; your cache remains safe.

Download the complete project, including `companion/static/`. Those are the production dashboard assets, already built in Codex Cloud. If Finder opens a `.command` file in a text editor, use Finder's Get Info → Open with → Terminal. The repository preserves the launchers' executable permissions; a Git clone preserves them most reliably.

## From then on

- **Update your data:** double-click `Refresh Garmin Data.command`, or use **Refresh data** inside the locally running dashboard.
- **View your dashboard:** double-click `Open Garmin Dashboard.command`.
- **Replace an expiring key:** double-click Setup again and choose to replace the existing local key.
- **Revisit older history/edits:** double-click `Refresh Full History.command`. It asks for an earliest health date and revisits all activity summaries and running files. This can be slow; normal Refresh is faster.

Normal refreshes check new activities plus the previous 14 days for changes, and resume incomplete health imports. Daily HR/Pulse Ox endpoints revisit two days. Garmin offers no documented updated-since feed, so older edits and remote deletions are not fully tracked automatically. Initial health history starts at the earliest activity date; if no activities exist it requests one year. Garmin may return no data for old dates.

## Secrets and local files

Setup saves your key only at `~/.config/garmin/connect-personal-api-key` with permissions that allow only your macOS user to read it. Garmin's official library exchanges that key for a temporary bearer token and caches the token beside it at `~/.config/garmin/connect-personal-api-bearer-token.json`, also user-only. Expiry is handled automatically. The app never displays either value, and neither goes into the frontend, SQLite database, URLs, Git, or logs.

Downloaded records live in `data/dashboard.sqlite3`. Original running FIT downloads live in `data/fit/`. All these files and `.venv/`, credentials, tokens, caches and environment files are excluded by `.gitignore`. **Compiled frontend assets are safe source deliverables and are committed. They contain no user records.** Synthetic test generators contain invented test inputs only and never run during normal use.

The SQLite cache and credential files are protected plaintext, not encrypted by this app. Enable FileVault and use encrypted backups. Anyone with access to your macOS user account can access local files. Original FIT files may contain precise GPS routes. Maps are disabled and route coordinates are removed from normalized dashboard data. Data is sent only to Garmin for API requests, never to telemetry, analytics or other APIs. Setup downloads software packages from the normal Python package registry, without Garmin data.

## Understanding availability

The UI shows missing sensor values as unavailable, not zero or invented metrics. Heart-rate zones appear when Garmin provides them. Best-distance segments and records are also derived locally from reliable FIT distance streams; credible Garmin-reported 5K results participate alongside sensor-validated results, with explicit evidence badges. Flagged results remain excluded from PBs. FIT speed and HR are required for decoupling and comparable-band trends. Data / Settings explains formulas and reports checked/partial/not-checked endpoints. Checked means the endpoint responded successfully, not that your device recorded every field.

First Mac sync still needs to verify live authentication, account-specific responses, original FIT decoding and the history Garmin actually makes available. Cloudflare prevented account testing in Codex Cloud. **No real Garmin data has been tested in this build.** This is a personal training tool, not medical advice or a diagnostic service.

## Development in Codex Cloud

The frontend source is React + TypeScript + Recharts. The companion uses Python 3.12+ and SQLite. Cloud development needs no Garmin key and must not call the live API.

```sh
npm ci
npm run build
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m companion serve --data-dir /tmp/stride-empty-test
```

Open `http://127.0.0.1:8765` in an environment-supported forwarded preview. Loopback on a remote machine is not your Mac; if the environment has no preview forwarding, browser QA can still run inside Cloud. The server intentionally rejects non-loopback Host headers. Do not publish your personal data to a cloud preview.

For an isolated populated development preview only:

```sh
PYTHONPATH=. python tests/seed_synthetic.py /tmp/stride-synthetic-test
python -m companion serve --data-dir /tmp/stride-synthetic-test --port 8766
```

This separate test database has a persistent synthetic-data banner and cannot sync from Garmin. Never point test seeding at your real data folder. Production startup defaults to `data/` and never loads fixtures. `npm run build` compiles the dashboard into `companion/static/`; commit those assets along with source so Mac users need only Python.

See [architecture and endpoint coverage](docs/ARCHITECTURE.md) and [validation report](docs/VALIDATION.md) for implementation details and limitations.

## Performance analytics update

Run Comparison, Aerobic Efficiency, HR at Pace, Fitness Trends, 5K Performance, Personal Records, Training Load, Recovery overlays, a month/week calendar and deterministic observations now extend the original dashboard. Run classifications explain their evidence and allow local overrides. Global dates/distance/classification filters, source-run links and mobile activity cards connect the views.

**Existing installation:** close the dashboard, pull the complete update including `companion/static/`, then double-click **Open Garmin Dashboard.command**. Migration is automatic and keeps the existing database and key. The first analysis may take longer while historical results are cached. Refresh normally with **Refresh Garmin Data.command**. No new production dependencies, Setup rerun, key re-entry, Node or npm are required. Full History is optional for revisiting old edits/missing FIT files.

See `docs/PERFORMANCE.md` for methods, sample thresholds, limitations, migration details and Mac validation steps. This update uses synthetic test data only; actual Garmin field availability, sensor quality and macOS Finder behavior still need checking on your Mac.

### Corrected 5K PBs and turnaround handling

Credible Garmin `fastestSplit_5000` results now count toward your 5K PB even if FIT reconstruction is unavailable or inconclusive. The 5K page uses one evidence-labelled performance table; brief bounded turnarounds are tolerated without removing elapsed time. Diagnostic reasons remain available for excluded results.

After pulling, close and reopen the dashboard: existing summaries are recalculated automatically. **No Setup rerun, database deletion, Full History refresh or API-key re-entry is needed.** Normal **Refresh Garmin Data.command** retries missing/incomplete FIT streams with cooldown. For one affected activity, open Run Detail → **Revalidate activity data** to force a fresh official FIT import immediately. Full History remains an optional, broader reimport. See `docs/FIVE_K.md`.
