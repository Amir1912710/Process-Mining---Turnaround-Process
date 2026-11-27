"""Package existing Berlin observations without changing or inventing source rows."""
from pathlib import Path
import csv,json,shutil,hashlib,zipfile
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/BER_Combined_Dataset'
OUT.mkdir(exist_ok=True)
PREP=ROOT/'data/ber_history/prepared'

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f);return rd.fieldnames,list(rd)

core_fields,core=read_csv(PREP/'ber_ground_intervals_core_proxy.csv')
_,all_pairs=read_csv(PREP/'ber_ground_intervals_proxy.csv')
assert len(core)==10940 and len(all_pairs)==11203
assert len({r['interval_id'] for r in core})==len(core)
for row in core:
    start=datetime.fromisoformat(row['inbound_last_seen_utc'])
    end=datetime.fromisoformat(row['outbound_first_seen_utc'])
    assert end>start
    assert abs((end-start).total_seconds()/60-float(row['ground_interval_proxy_min']))<.001
    assert not any(row[k] for k in ['actual_landing_time','actual_inblock_time','actual_offblock_time','actual_takeoff_time'])

primary=OUT/'BER_Combined_Turnaround_Pairs.csv'
shutil.copy2(PREP/'ber_ground_intervals_core_proxy.csv',primary)
shutil.copy2(PREP/'ber_ground_intervals_proxy.csv',OUT/'BER_All_Candidate_Pairs_With_Review_Flags.csv')
support=OUT/'supporting_prepared_data';support.mkdir(exist_ok=True)
for p in PREP.iterdir():
    if p.is_file() and p.suffix in ['.csv','.json'] and p.name not in ['ber_ground_intervals_core_proxy.csv','ber_ground_intervals_proxy.csv']:
        shutil.copy2(p,support/p.name)

daily=[]
for p in sorted((ROOT/'data/acdm/days').glob('*/flights.csv')):
    _,rows=read_csv(p);daily.append({'source_day':p.parent.name,'records':len(rows)})
    dest=OUT/'ACDM_daily_snapshots'/p.parent.name;dest.mkdir(parents=True,exist_ok=True)
    for name in ['flights.csv','flights.json','manifest.json']:
        src=p.parent/name
        if src.exists():shutil.copy2(src,dest/name)

refs=OUT/'ACDM_supplemental_reference';refs.mkdir(exist_ok=True)
for p in (ROOT/'data/ber_history/acdm_current_reference').iterdir():
    if p.is_file() and (p.name=='manifest.json' or p.name.startswith('page_')) and p.suffix=='.json':shutil.copy2(p,refs/p.name)
shutil.copy2(ROOT/'data/ber_history/README.md',support/'historical_preparation_method.md')

readme=f'''# Combined Berlin dataset — packaged 19 November 2026

## Open this file first

`BER_Combined_Turnaround_Pairs.csv`: **{len(core):,} rows and {len(core_fields)} columns**. This is an unchanged copy of the pairing-screened core table used for the thesis. Each row is a candidate interval between an inbound and following outbound observation of the same aircraft ICAO24 identifier at BER (EDDB). It joins two flight legs; it is not one flight leg or a certified ground-truth rotation.

**{sum(bool(r['acdm_reference_key']) for r in core):,} rows have a candidate A-CDM reference match.** The other rows retain their OpenSky pairing, with missing A-CDM fields left empty. A-CDM matches are based on unique callsign/time correspondence, not independent registration-to-ICAO24 verification.

## Timestamp meanings

- `inbound_last_seen_utc` / `inbound_last_seen_berlin`: last observed inbound flight boundary.
- `outbound_first_seen_utc` / `outbound_first_seen_berlin`: first observed outbound flight boundary.
- `ground_interval_proxy_min`: outbound first-seen minus inbound last-seen, in minutes.
- `actual_landing_time`, `actual_inblock_time`, `actual_offblock_time`, `actual_takeoff_time`: empty; these exact operational events were not independently observed for the paired rows.
- `acdm_actual_takeoff_naive`: an actual-takeoff field from the matched A-CDM record where available; preserved in its source timezone form. `acdm_timezone_hypothesis` records the reconciliation hypothesis separately.

Therefore, this table approximates the aircraft's arrival-to-next-departure interval. **It is not exact measured landing-to-takeoff or stand turnaround (AIBT–AOBT).** TOBT and TSAT are targets, not executed service events. Cleaning, fueling, boarding and passenger counts are not measured in this dataset. No simulated service times have been inserted.

## Coverage and other files

The core arrivals range from {min(r['inbound_last_seen_berlin'] for r in core)} to {max(r['inbound_last_seen_berlin'] for r in core)}. There are 54 supporting September 30 arrivals paired to departures entering the October period. The core table does not provide complete coverage through November 19.

`BER_All_Candidate_Pairs_With_Review_Flags.csv` contains **{len(all_pairs):,} candidates**, including the {len(all_pairs)-len(core):,} omitted from the screened table. It has {sum(bool(r['acdm_reference_key']) for r in all_pairs):,} candidate A-CDM links. Some observations reach November 12, but sparse/missing coverage and other flags make these rows unsuitable for automatic inclusion. This table and the core table overlap; do not concatenate them.

`supporting_prepared_data/` contains the original movements, unmatched departures, daily coverage, reference cross-checks and preparation audit. The 1,204 observed A-CDM takeoff records and 1,230 cross-check reference records are earlier historical-build views with supplemental partial-day observations. They overlap other A-CDM views; their counts must not be added together as distinct flights.

`ACDM_daily_snapshots/` contains all five finalized snapshots currently saved: {', '.join(d['source_day']+' ('+str(d['records'])+' rows)' for d in daily)}. Their total is {sum(d['records'] for d in daily):,} departure records across five separated snapshots, not a continuously observed period or a set of fully completed turnarounds. These source records can include unfinished/canceled departures. The November 15/16 snapshots were collected after the combined table was built. They are included separately and are **not silently appended as paired turnarounds**, because corresponding OpenSky arrivals are unavailable in this build.

`ACDM_supplemental_reference/` preserves the existing supplemental reference response pages and manifest used in the earlier build. It is not an additional complete day.

## Main column groups

| Columns | Meaning |
|---|---|
| `interval_id` | Unique candidate interval key |
| `aircraft_icao24` | Physical-aircraft identifier used for pairing, subject to surveillance/identity limitations |
| `inbound_callsign`, `outbound_callsign` | ATC identifiers for the two legs; not necessarily commercial flight numbers |
| `inbound_origin`, `outbound_destination` | Source airport context |
| UTC and Berlin boundary columns | Offset-aware observation-boundary timestamps |
| `ground_interval_proxy_min`, `descriptive_duration_band` | Arithmetic interval and descriptive stay band |
| `timing_basis`, `pairing_basis`, `review_flags`, `eligible_core_proxy_cohort` | Definitions and screening status; core does not mean verified timing |
| Distance/alternative-airport columns | Airport-estimation quality context |
| Source-file and outbound-flight keys | Provenance links to archived source records |
| `acdm_reference_key`, candidate reference fields | Matched A-CDM registration, type, airline, stand, runway and targets where available |
| `acdm_actual_takeoff_naive`, `acdm_timezone_hypothesis`, `opensky_departure_minus_acdm_min`, `acdm_match_basis` | Departure cross-check, original timestamp and explicitly recorded matching assumptions |

## Checks

The packaging script checks unique core IDs, positive interval ordering, minute arithmetic and absence of fabricated exact-event timestamps. Exported CSVs are byte-identical copies; preparation screening is not rerun or changed. The original verification report documents source aircraft/airport/time linkage checks. `dataset_manifest.json` records file hashes and counts. No API credentials, authentication responses or simulated service logs are included.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
manifest={'packaged_on':'2026-11-19','primary_rows':len(core),'primary_columns':len(core_fields),'primary_candidate_acdm_matches':sum(bool(r['acdm_reference_key']) for r in core),'all_candidates':len(all_pairs),'daily_acdm_snapshots':daily,'exact_measured_landing_to_takeoff_rows':0,'paired_table_updated_with_newer_snapshots':False,'files':{str(p.relative_to(OUT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='dataset_manifest.json'}}
(OUT/'dataset_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=ROOT/'output/BER_Combined_Dataset.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(OUT))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
assert hashlib.sha256(primary.read_bytes()).digest()==hashlib.sha256((PREP/'ber_ground_intervals_core_proxy.csv').read_bytes()).digest()
print(json.dumps({'csv':str(primary),'archive':str(archive),'archive_mb':round(archive.stat().st_size/1e6,2),'rows':len(core),'candidate_acdm_links':manifest['primary_candidate_acdm_matches'],'finalized_acdm_source_records':sum(d['records'] for d in daily)},indent=2))
