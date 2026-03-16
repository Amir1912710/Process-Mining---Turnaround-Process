# Data Quality Report

## Dataset Overview
- Turnaround cases: 28417
- Event log cases: 27944
- Event rows: 111776

## Event Log Consistency
- Expected events per case (median observed): 4
- Cases with unexpected event counts: 0
- Cases with timestamp ordering failures: 0

## Enrichment Completeness
- airline: 4825 missing (16.98%)
- aircraft_type: 5931 missing (20.87%)
- turnaround_airport_country: 190 missing (0.67%)
- turnaround_airport_latitude: 190 missing (0.67%)
- turnaround_airport_longitude: 190 missing (0.67%)

## Turnaround Duration Distribution (minutes)
- count: 28417.0
- mean: 86.84
- std: 42.69
- min: 15.0
- 25%: 58.62
- 50%: 78.15
- 75%: 106.05
- 90%: 146.17
- max: 239.78

## Notes
- ALDT/AIBT/AOBT/ATOT are proxy milestones derived from OpenSky-style flight timestamps and configurable taxi assumptions.
- Missing airline enrichment is expected when callsign prefixes do not match OpenFlights reference data.