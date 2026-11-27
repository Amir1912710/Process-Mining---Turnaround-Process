# Policy and clock review — 13 November 2026

The no-curfew scenario is an assumption sensitivity. It is not a proposed operational model for BER.

BER's own guidance states a core night-flight restriction from 00:00 to 05:00, with additional constraints during 23:00–24:00 and 05:00–06:00. [Airport guidance](https://corporate.berlin-airport.de/de/nachhaltigkeit/umwelt/fluglaerm/hinweise-zum-nachtflug.html). The airport's [2024 noise report](https://corporate.berlin-airport.de/content/dam/corporate/de/unternehmen-presse/newsroom/publikationen/fluglaermbericht/2024-fluglaermbericht.pdf) distinguishes generally permitted scheduled operations in 22:00–23:30 and 05:30–06:00 from early/delayed movements in the adjacent half-hour windows. Exceptions and quotas require a separate operational model; the current data do not identify eligibility for every flight.

The official [cpnsim source](https://github.com/rwth-pads/cpnsim/blob/main/src/simulator.rs) implements `sim_time_to_datetime` as a UTC datetime and `rhai_hour_of_day` reads its hour. The study epoch is UTC midnight. Consequently the inherited `hour_of_day(t) < 5` condition evaluates 00:00–05:00 **UTC**. On November 1 and November 8, Berlin is UTC+1: that condition corresponds to 01:00–06:00 local time. This is a confirmed clock-semantics mismatch for the modeled local night window, not merely an uncertainty about whether BER has restrictions.

A minimal probe against the actual installed cpnsim 0.6.2 WASM runtime also returned hour 0 at epoch `2026-11-01T00:00:00Z`, when Berlin local hour is 1. Results are saved in `clock_probe.json`; this conclusion does not rely only on the current repository source.

The inherited policy is applied to cleaning-complete → pre-boarding availability (e106) and start-up approval → pushback clearance (e191), with random release spread across the next opening hour. The airport sources describe takeoff/landing restrictions. They do not establish the model's separate pre-boarding embargo. This is an inference about model scope: a future implementation must distinguish ground handling, movement eligibility, departure scheduling, exceptions, and local-time windows.

The frozen v2.1 experiment intentionally retains the inherited implementation in its inherited-policy cells, and disables the whole helper in its no-curfew cells. It measures dependence on that implementation. It must not be described as comparing BER-compliant and BER-noncompliant flights, or as establishing that no-curfew is the preferred real policy.

Next realistic model version: explicitly use Europe/Berlin time (including daylight-saving changes for the full period), represent core/shoulder windows and exception categories, and apply policy at the relevant movement/clearance boundary without blocking unrelated cabin work by assumption. Freeze this specification before outcome-based evaluation. Keep existing v2.0/v2.1 results as separate analyzed references.
