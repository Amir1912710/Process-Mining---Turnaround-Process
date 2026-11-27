# MSc Thesis Artifacts

Data, scripts, models and results of the MSc thesis
**Data-Driven Object-Centric Simulation for Airport Turnaround Analysis and Resource Optimization**
(Amir Abdelsayed, ELTE Faculty of Informatics, Data Science MSc, 2026).

Appendix B of the thesis refers to this folder.

## Contents

| Folder | What it contains | Thesis |
|---|---|---|
| `data/acdm/` | BER A-CDM departure board, collected daily: raw responses (`raw/`), daily snapshots with manifests and SHA-256 hashes (`days/`), prepared tables | Sec. 4.1.1, 6.1 |
| `data/ber_history/` | OpenSky arrivals/departures of BER (30 Sep–9 Nov 2026) and access checks | Sec. 4.1.2–4.1.3 |
| `data/weather/` | Hourly Open-Meteo weather for BER | Sec. 4.1.4 |
| `data/febapr/cleaned_dataset.csv` | 2,070 manually recorded turnarounds, Feb–Apr 2026 | Sec. 4.1.5 |
| `models/baseline/airport-extended.ocpn` | Unchanged *Airport Ground Handling (Extended)* model from OCPN Studio | Sec. 4.3.1 |
| `output/acdm_primary_20261119/` | 1,322 A-CDM records with OpenSky cross-check (`ACDM_Berlin_Primary_With_OpenSky_Check.csv`), observed departure OCEL | Sec. 6.1 |
| `output/BER_Combined_Dataset/` | 10,940 candidate turnarounds (`BER_Combined_Turnaround_Pairs.csv`) | Sec. 4.1.3 |
| `output/early_warning/` | Delay drivers, early-warning classifiers, disruption screening | Sec. 6.2 |
| `output/study_v3/` | Timing comparison (original, literature, carrier) on 41 days | Sec. 6.4 |
| `output/calibration_v3/` | Calibration grid: built models and results | Sec. 6.4.3, App. A |
| `output/validation_nov15_16/` | Held-out validation days 15–16 Nov | Sec. 6.4.3 |
| `output/whatif_v3/` | What-if scenarios on 41 days | Sec. 6.6 |
| `output/controlled_study_v21/`, `output/controlled_study_v22/` | Earlier controlled study and Monte Carlo replications | Sec. 6.3, App. A |
| `output/ocel_v3/` | Calibrated OCEL 2.0 logs, models, case tables and manifests | Sec. 6.5 |
| `output/process_mining_v3/` | PM4Py discovery, flattening and conformance results | Sec. 6.5.4–6.5.5 |
| `output/Promenade_Analysis/`, `promenade/` | Promenade exports and screenshots | Sec. 6.5.6 |
| `output/*_v4/`, `output/v4_logs/` | **Baggage sensitivity run (v4).** Same design as v3, but narrow-body baggage unloading/loading use carrier-specific literature times (`baggage='carrier'`, function `bag_sec`) instead of the baseline `hold_sec`: calibration (`calibration_v4`), held-out validation (`validation_nov15_16_v4`), 41-day timing study (`study_v4`), what-if study (`whatif_v4`), OCEL logs (`ocel_v4`) and process mining (`process_mining_v4`). The thesis results are v3; v4 is reported as a sensitivity analysis | Sec. 4.3.6, 6.5.2 |
| `tools/` | All collection, linkage, simulation and analysis scripts | Ch. 5, App. B |
| `thesis_latex/` | LaTeX sources and figures of the thesis | – |

## Main scripts (`tools/`)

| Script | Purpose |
|---|---|
| `acdm_collect.py` | Daily A-CDM collector (needs an API key, not included) |
| `collect_ber_opensky.py`, `build_ber_history.py` | OpenSky retrieval and movement table |
| `prepare_turnaround_linkage.py`, `link_acdm_opensky.py` | Candidate turnarounds and A-CDM linkage |
| `enrich_turnarounds.py` | Airline, carrier class, aircraft type, weather |
| `new_empirical_analyses.py` | Empirical properties P1–P4 |
| `febapr_propagation.py` | Held-out delay-transfer model |
| `delay_drivers_early_warning.py` | Delay drivers, early warning, disruption screening |
| `build_msc_ocpn.py` | Model builder |
| `run_msc_ocpn.mjs`, `run_controlled_ocpn.mjs`, `export_msc_ocel.mjs` | Headless CPNsim runner and OCEL export |
| `run_v3_study.py`, `calibrate_v3.py`, `run_whatif_v3.py` | Timing study, calibration, what-if study |
| `build_validation_days.py`, `validate_new_days.py`, `validate_nov8_refs.py` | Held-out validation |
| `process_mining_v3.py` | Process mining with PM4Py |
| `run_all_v4.py` | Runs the complete baggage sensitivity study (v4) in order: `calibrate_v4.py`, `validate_new_days_v4.py`, timing study, `run_whatif_v4.py`, analyses, `export_ocel_v4.py`, process mining |

## Requirements

- Simulation: Node.js 24 and `@rwth-pads/cpnsim` 0.6.2
- Analysis: Python 3.14 with NumPy 2.3.4, pandas 2.3.3, SciPy 1.16.3, scikit-learn 1.7.2, PM4Py 2.7.19, Matplotlib 3.10.7

The CPNsim runtime does not expose seed control, so repeated simulation runs produce new stochastic outcomes. The analysis scripts use fixed seeds.

## Data sources and terms

- A-CDM data: BER A-CDM application (Flughafen Berlin Brandenburg GmbH).
- Flight observations: [The OpenSky Network](https://opensky-network.org/).
- Weather: [Open-Meteo](https://open-meteo.com/) historical archive (ERA5).

The data are shared for research reproducibility. Use of the source data remains subject to the terms of the respective providers. API credentials are not part of this repository.
