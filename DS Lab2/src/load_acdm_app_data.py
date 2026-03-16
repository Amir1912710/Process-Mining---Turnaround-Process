"""Load manually captured Airport CDM app observations into structured datasets.

This module is intended for data that the user can legitimately access in the app and then
export or transcribe to CSV. It does not attempt to bypass app access controls.
"""

from __future__ import annotations

import argparse
from zoneinfo import ZoneInfo

import pandas as pd

from src.airline_segments import (
    classify_airline_records,
    derive_airline_code_candidates,
    enrich_airline_names,
)
from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import normalise_airport_code, normalise_callsign, read_table, setup_logging, write_table


REQUIRED_COLUMNS = [
    "snapshot_taken_local",
    "observation_date_local",
    "callsign",
    "flight_number",
    "origin_airport_icao",
    "destination_airport_icao",
]


def _localize_timestamp(series: pd.Series, timezone_name: str) -> pd.Series:
    # Parse row by row so mixed AM/PM patterns in manually entered screenshots
    # do not get coerced to NaT by a single inferred format.
    local_dt = series.map(lambda value: pd.to_datetime(value, errors="coerce"))
    tz = ZoneInfo(timezone_name)

    def _convert(value):
        if pd.isna(value):
            return pd.NaT
        if value.tzinfo is None:
            return value.tz_localize(tz).tz_convert("UTC")
        return value.tz_convert("UTC")

    return local_dt.map(_convert)


def _parse_local_time_column(
    df: pd.DataFrame,
    date_col: str,
    time_col: str,
    timezone_name: str,
) -> pd.Series:
    if time_col not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    time_text = (
        df[time_col]
        .astype("string")
        .str.strip()
        .replace({"": pd.NA, "-": pd.NA, "—": pd.NA, "–": pd.NA, "None": pd.NA})
    )
    date_text = df[date_col].astype("string").str.strip()
    return _localize_timestamp(date_text + " " + time_text, timezone_name)


def normalize_acdm_app_data(
    df: pd.DataFrame,
    timezone_name: str,
    airline_reference_path,
    segment_config_path=None,
) -> pd.DataFrame:
    """Normalize manually captured app data into a consistent schema."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"A-CDM app input is missing required columns: {missing}")

    normalized = df.copy()
    normalized["callsign"] = normalise_callsign(normalized["callsign"])
    normalized["flight_number"] = normalized["flight_number"].astype("string").str.strip().str.upper()
    normalized["origin_airport_icao"] = normalise_airport_code(normalized["origin_airport_icao"])
    normalized["destination_airport_icao"] = normalise_airport_code(normalized["destination_airport_icao"])
    normalized["app_airport_icao"] = normalise_airport_code(
        normalized["app_airport_icao"] if "app_airport_icao" in normalized.columns else normalized["origin_airport_icao"]
    )
    normalized["status"] = normalized.get("status", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip()
    normalized["aircraft_type"] = normalized.get("aircraft_type", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip().str.upper()
    normalized["aircraft_registration"] = normalized.get("aircraft_registration", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip().str.upper()
    normalized["gate"] = normalized.get("gate", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip()
    normalized["position"] = normalized.get("position", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip()
    normalized["runway"] = normalized.get("runway", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip().str.upper()
    normalized["sid"] = normalized.get("sid", pd.Series(index=normalized.index, dtype="string")).astype("string").str.strip().str.upper()
    normalized["taxitime_minutes"] = pd.to_numeric(normalized.get("taxitime_minutes"), errors="coerce")

    normalized["snapshot_taken_utc"] = _localize_timestamp(normalized["snapshot_taken_local"], timezone_name)
    for prefix in ["display_time", "eobt", "tobt", "tsat", "ctot"]:
        normalized[f"{prefix}_utc"] = _parse_local_time_column(
            normalized,
            date_col="observation_date_local",
            time_col=f"{prefix}_local",
            timezone_name=timezone_name,
        )

    candidates = derive_airline_code_candidates(normalized, callsign_col="callsign", flight_number_col="flight_number")
    normalized = pd.concat([normalized.reset_index(drop=True), candidates.reset_index(drop=True)], axis=1)
    normalized = normalized.rename(
        columns={
            "airline_iata_candidate": "airline_iata_code",
            "airline_icao_candidate": "airline_icao_code",
        }
    )

    normalized = enrich_airline_names(
        normalized,
        reference_path=airline_reference_path,
        airline_col="airline",
        iata_col="airline_iata_code",
        icao_col="airline_icao_code",
    )
    normalized = classify_airline_records(
        normalized,
        segment_config_path=segment_config_path,
        airline_col="airline",
        iata_col="airline_iata_code",
        icao_col="airline_icao_code",
        callsign_col="callsign",
    )

    normalized["case_id"] = normalized.apply(
        lambda row: f"APP_{row['observation_date_local']}_{row['origin_airport_icao']}_{row['callsign']}_{row.name:04d}",
        axis=1,
    )
    return normalized


def load_acdm_app_data(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
    segment_config_path: str | None = None,
    timezone_name: str = "Europe/Berlin",
) -> pd.DataFrame:
    """Load A-CDM app observations from a CSV/Parquet file."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    source = resolve_path(input_path, project_root) if input_path else paths["raw_dir"] / "acdm_app_observations_sample.csv"
    destination = resolve_path(output_path, project_root) if output_path else paths["interim_dir"] / "acdm_app_snapshots.parquet"

    reference_path = paths["raw_dir"] / config["sources"]["openflights_airlines"]["raw_filename"]
    logger.info("Reading A-CDM app observations from %s", source)
    raw = read_table(source)
    normalized = normalize_acdm_app_data(
        raw,
        timezone_name=timezone_name,
        airline_reference_path=reference_path if reference_path.exists() else None,
        segment_config_path=segment_config_path,
    )
    write_table(normalized, destination)
    logger.info("A-CDM app snapshots saved to %s", destination)
    return normalized


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Path to manually captured A-CDM app observations.")
    parser.add_argument("--output-path", help="Output path for normalized A-CDM app data.")
    parser.add_argument("--segment-config", default="configs/airline_segments.yaml", help="Airline segment mapping file.")
    parser.add_argument("--timezone", default="Europe/Berlin", help="Timezone used in the app screenshots.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    load_acdm_app_data(
        config_path=args.config,
        input_path=args.input_path,
        output_path=args.output_path,
        segment_config_path=args.segment_config,
        timezone_name=args.timezone,
    )


if __name__ == "__main__":
    main()
