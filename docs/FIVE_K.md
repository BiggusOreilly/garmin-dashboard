# 5K evidence, validation and revalidation

The previous code rejected an entire candidate if a single interval had implied movement below 0.5 m/s, a sampling gap over 10 s or disagreement between instantaneous speed and cumulative distance. A genuine turnaround could therefore invalidate an otherwise continuous 5K. Separately, PB progression ignored Garmin `fastestSplit_5000` entirely: only `records['5 km']` was eligible. Failure to reconstruct a result was incorrectly treated as absence of a credible performance.

## One result and an explicit evidence hierarchy

Each activity now has one canonical `fiveKPerformance`, used by the 5K page, Personal Records, Overview, Running Trends, Fitness Trends and PB observations. Local reconstructions remain available in `records`, and `fiveKValidation` retains diagnostic reasons. One activity contributes at most one performance/event to a list.

- **Sensor validated:** an independently reconstructed 5,000 m result. If it is faster than the Garmin result, prefer it. Times within two seconds are treated as corroborated rounding/interpolation agreement; preserve the better credible time and disclose `sensorSeconds`/the agreement in validation details when needed.
- **Garmin reported:** an explicit Garmin 5K split that beats the local result or cannot be corroborated locally. Missing, short, gapped or unusable local streams are inconclusive, not proof of an invalid Garmin result. These results remain PB-eligible and enter history and trends. Never populate segment HR, cadence or splits from whole-activity averages.
- **Flagged:** clear contradictory evidence such as a distance reset/teleport, impossible overall 5K pace, a reported time exceeding known activity elapsed time, or a summary distance below 4,500 m. Downhill >1% remains excluded under the existing policy. Merely having a bad speed field with otherwise plausible cumulative distance does not disprove Garmin's reported result. Flagged candidates are visible with an exclusion reason and do not enter progression. If the activity has a separate credible local best, it can still contribute that best; a rejected reported alternative is disclosed in its quality note.

Near-5K summary duration alone is not an exact 5K record. Garmin-reported results do not imply an official race or certified distance. Title cues remain provisional. Unknown elevation is disclosed, not invented.

## Bounded 5K tolerance

Use cumulative **travelled** distance, never straight-line displacement or coordinates. Candidate time is the full elapsed duration; near-stop time is never subtracted. Search sample starts and interpolate the end crossing as before.

Only the 5K search tolerates short near-stops or small speed/distance wobbles. All of these must hold:

- No more than three separate questionable episodes. Consecutive bad samples form one episode, making the rule independent of 1 s versus 5 s recording frequency.
- Total questionable time ≤12 s **and** ≤1% of the candidate elapsed duration.
- Longest consecutive questionable section ≤8 s.
- Affected travelled distance ≤30 m (also capped at 1% of target distance).
- An isolated non-stationary speed/distance discrepancy represents ≤20 m of disagreement for its interval.

Sampling gaps >10 s, decreasing cumulative distance, non-increasing time, distance teleports implying >10 m/s and overall 5K speed >7 m/s remain rejected. A sustained stop or repeated wobbles exceeding the budgets cannot become a clean continuous sensor record. Shorter/other-distance records retain strict interval rules. Aerobic HR/pace sampling gates are unchanged.

A “turnaround-like” flag means a brief near-stop pattern, not an inferred geographic direction change. No heading or GPS coordinates are read or returned. Small anomalies are tolerated using observed cumulative distance; the algorithm does not invent replacement distance.

## Diagnostics and UI

A single primary table shows the chosen time, source activity, evidence, segment sensor metrics where available, splits, half change, final kilometre and quality note. Expand **Validation details** in the table or Run Detail for invalid-interval count, invalid duration, longest invalid interval/section, minimum implied speed, largest speed disagreement, maximum sample gap, reset detection and near-stop pattern. Garmin-only unavailable fields display `—`. PB chart points distinguish filled sensor dots from outlined Garmin dots; tooltips/event rows retain the evidence label.

## FIT retry lifecycle

Normal refresh examines cached series even for older activities. Retry missing/empty/failed parsing, unusable distance/time data, substantial missing sections, recordings under 95% of summary distance, insufficient distance for an explicitly reported 5K, or severe cumulative-distance problems. Missing HR/cadence alone and ordinary turnarounds do not trigger downloads.

Reparse a cached local original first; download through the existing official client if that remains unusable. A changed source summary triggers a fresh download. Healthy unchanged history is not downloaded repeatedly. Retry metadata is stored locally under `fit:<activity id>` in the existing metadata table, with 1, 2, 4, 8, 16 then 30-day cooldowns after repeated failures. A failed or worse response preserves the better existing series and original file. These are retry thresholds, not physiology or injury rules.

**Revalidate activity data** in Run Detail forces a download/reparse for that activity and bypasses cooldown. It uses the existing server and process import locks, local-write protections and official client; marked synthetic databases cannot use it. Completion reloads the selected activity and derived analysis. **Refresh Full History.command** deliberately forces all running originals, as a broader optional operation.

## Existing installation and privacy

Analysis fingerprint version 7 invalidates old derived calculations automatically. No schema migration, dependency change, database deletion, key re-entry, Setup rerun or Node/npm installation is required. Close the dashboard, pull the update including production assets, and reopen. Already-imported Garmin 5K splits participate immediately. Use normal Refresh for automatic FIT recovery, or the per-activity action for immediate recovery. Full History is not required to correct PB selection.

Garmin credentials, bearer-token handling, the official adapter, GPS projection, local storage and ignore protections are unchanged. No personal data was used in this update. Live device sampling, original availability and the reported activity can only be validated after refreshing locally on the Mac.
