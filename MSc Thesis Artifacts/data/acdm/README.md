# BER A-CDM daily collection

Current user request: cancel hourly historical backfill and collect each newly completed day once daily, using the same corrected method as the November 1 snapshot. Schedule: **00:15 Europe/Berlin**. For example, the run on November 3 at 00:15 collects November 2. The computer and app must be running.

## Execution

Working directory: `C:\Users\amira\Documents\ChatGPT\Thesis Project`.

```powershell
& 'C:\Users\amira\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 tools/acdm_collect.py
```

The existing chat automation `a-cdm` was updated in place to run daily. There is no separate hourly job. State uses `collection_mode=end_of_day`. The collector calculates the previous Berlin calendar date with DST awareness, skips already-saved dates, and takes an exclusive lock. The old October backfill cursor is no longer used. Do not catch up multiple dates or use the manual repair flag in scheduled runs. Respect HTTP 429/Retry-After. If a day is unavailable or collection fails, record and report that failure; future daily runs continue to select the newly completed day.

The existing credential was recovered from the user's ChatGPT project chat **API data collection**. It is protected with Windows DPAPI for this Windows user in `.secrets/acdm-api-key.dpapi`. Do not print its contents or put the key in source, reports, manifests or logs.

The saved snapshot for **2026-11-01** contains **289 records**, including 283 takeoffs, 5 canceled flights and 1 scheduled flight. The initial six-record snapshot used `filterAtot=1`, which hid flights that had taken off. The collector now always uses **`filterAtot=0`** and retrieves every API page, saving only the requested raw STD date. Independent completeness remains unverified. The next new target date is **2026-11-02**, to be collected after that day ends.

Historical check: a full seven-page request for October 31 using the corrected filter returned 666 records dated November 1–3 and zero dated October 31. The user then canceled historical backfill. This endpoint is used for recent completed-day snapshots; do not resume archive probing automatically.

## Outputs

- `state.json`: daily mode and schedule, most recent attempt, status and successfully saved date snapshots. `completed_days` means saved snapshots, not independently verified complete daily coverage. The actual scheduled target is always yesterday in Europe/Berlin.
- `days/YYYY-MM-DD/flights.json` and `flights.csv`: only records whose raw API `std` starts with the requested calendar date; all supplied fields retained.
- `days/YYYY-MM-DD/manifest.json`: endpoint, collection time, pagination, counts, date selection, coverage caveat and raw-response hashes.
- `raw/YYYY-MM-DD/page_NNN.json`: exact API page responses for audit; these can contain other dates because the endpoint returns a live board. They must not be treated as additional collected target days.
- `attempts/YYYY-MM-DD.json`: evidence of a requested historical date not returned by the board.
- `superseded/YYYY-MM-DD/filterAtot1/`: preserved original incomplete snapshot and raw pages from the filter error. Exclude these from the usable dataset to avoid duplicate or incomplete versions.

`--repair-last-snapshot` was used once interactively to correct November 1. Scheduled runs must use the default command without this flag.

## Interpretation

API timestamp values have no timezone offset. Preserve them unchanged and do not claim verified Europe/Berlin or UTC semantics. Date membership currently uses their literal STD calendar date. The query uses a conservative earlier UTC lower bound and client-side exact-date filtering, because a reliable dateTo/archive filter has not been established.

No missing values are invented. Retain estimated/target/actual milestone distinctions. Do not merge these observations with `BER_Turnarounds_MIXED_REAL_SYNTHETIC.csv` as if the latter were all real observations. Raw collection is not yet a model-ready or independently validated dataset.

Routine successful daily runs and duplicate checks remain quiet. Notify on a new collection failure, required user action or meaningful dataset milestone. Local execution requires this computer and the app to be running.
