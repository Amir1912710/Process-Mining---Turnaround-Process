# Airline Segment Comparison

This report compares low-cost and full-service carriers using the processed turnaround dataset and, when available, the manually captured A-CDM app snapshot dataset.

## Highlights
- Low-cost carriers show the shorter mean turnaround in the current turnaround dataset by 13.80 minutes.
- Full-service carriers show the larger 90th percentile turnaround by 28.89 minutes.
- Low-cost carriers show lower average app-reported taxi time by 0.52 minutes.

## Turnaround Summary
| airline_segment | cases | unique_airlines | mean_turnaround_minutes | median_turnaround_minutes | p90_turnaround_minutes | unique_airports |
| --- | --- | --- | --- | --- | --- | --- |
| full_service | 9253 | 96 | 95.6 | 88.12 | 147.81 | 599 |
| low_cost | 3991 | 21 | 81.8 | 73.55 | 118.92 | 295 |

## Top Turnaround Airports
| airline_segment | airport_icao | cases |
| --- | --- | --- |
| full_service | KATL | 336 |
| full_service | EHAM | 313 |
| full_service | KORD | 299 |
| full_service | EDDF | 264 |
| full_service | LFPG | 242 |
| full_service | EGLL | 240 |
| full_service | KDFW | 203 |
| full_service | EDDM | 197 |
| full_service | KCLT | 177 |
| full_service | EKCH | 155 |
| low_cost | LEBL | 117 |
| low_cost | KLAS | 110 |
| low_cost | KDEN | 97 |
| low_cost | KBWI | 96 |
| low_cost | KMCO | 96 |
| low_cost | EGKK | 88 |
| low_cost | KPHX | 85 |
| low_cost | EGSS | 82 |
| low_cost | KMDW | 79 |
| low_cost | KBNA | 75 |

## A-CDM App Milestone Summary
| airline_segment | flights | mean_taxitime_minutes | mean_tsat_minus_tobt_minutes | mean_ctot_minus_tsat_minutes | mean_eobt_minus_tobt_minutes |
| --- | --- | --- | --- | --- | --- |
| full_service | 27 | 14.52 | 1.33 | 14.17 | -7.92 |
| low_cost | 3 | 14.0 | 0.0 |  | 0.0 |

## A-CDM App Top Routes
| airline_segment | route | flights |
| --- | --- | --- |
| full_service | EDDF -> KDFW | 2 |
| full_service | EDDB -> EDDM | 1 |
| full_service | EDDB -> EKCH | 1 |
| full_service | EDDF -> CYUL | 1 |
| full_service | EDDF -> EDDH | 1 |
| low_cost | EDDB -> OLBA | 1 |
| low_cost | EDDF -> LTAC | 1 |
| low_cost | EDDL -> OMDW | 1 |