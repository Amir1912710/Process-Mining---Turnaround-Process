"""Normalize and validate OpenSky-like flight data."""

from __future__ import annotations

import argparse
import re
from typing import Iterable

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import (
    normalise_airport_code,
    normalise_callsign,
    normalise_icao24,
    parse_utc_datetime,
    read_table,
    setup_logging,
    write_table,
)


COLUMN_CANDIDATES: dict[str, list[str]] = {
    "icao24": ["icao24", "icao_24", "icao"],
    "callsign": ["callsign", "call_sign", "flight", "flight_number", "flightnumber"],
    "departure_time": ["firstseen", "departure_time", "departure_timestamp", "dep_time", "out_time"],
    "arrival_time": ["lastseen", "arrival_time", "arrival_timestamp", "arr_time", "in_time"],
    "origin_airport_icao": [
        "estdepartureairport",
        "departure_airport_icao",
        "origin_airport",
        "origin",
        "adep",
        "departure_airport",
    ],
    "destination_airport_icao": [
        "estarrivalairport",
        "arrival_airport_icao",
        "destination_airport",
        "destination",
        "ades",
        "arrival_airport",
    ],
}

CRITICAL_COLUMNS = [
    "icao24",
    "departure_time",
    "arrival_time",
    "origin_airport_icao",
    "destination_airport_icao",
]


def _canonical_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _canonical_lookup(columns: Iterable[str]) -> dict[str, str]:
    return {column: _canonical_name(column) for column in columns}


def normalize_flight_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns from OpenSky-like exports to a consistent schema."""
    lookup = _canonical_lookup(df.columns)
    rename_map: dict[str, str] = {}

    for target, candidates in COLUMN_CANDIDATES.items():
        canonical_candidates = {_canonical_name(candidate) for candidate in candidates}
        for original, canonical in lookup.items():
            if canonical in canonical_candidates:
                rename_map[original] = target
                break

    normalized = df.rename(columns=rename_map).copy()
    missing = [column for column in CRITICAL_COLUMNS if column not in normalized.columns]
    if missing:
        raise ValueError(
            "Missing critical columns after normalization: "
            + ", ".join(missing)
            + ". Available columns: "
            + ", ".join(df.columns.astype(str))
        )

    if "callsign" not in normalized.columns:
        normalized["callsign"] = pd.NA

    return normalized


def clean_flights_df(df: pd.DataFrame, logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean flight-level data and return the cleaned table plus drop statistics."""
    df = normalize_flight_columns(df)
    initial_rows = len(df)

    df["icao24"] = normalise_icao24(df["icao24"])
    df["callsign"] = normalise_callsign(df["callsign"])
    df["origin_airport_icao"] = normalise_airport_code(df["origin_airport_icao"])
    df["destination_airport_icao"] = normalise_airport_code(df["destination_airport_icao"])
    df["departure_time"] = parse_utc_datetime(df["departure_time"])
    df["arrival_time"] = parse_utc_datetime(df["arrival_time"])

    drop_masks = {
        "missing_icao24": df["icao24"].isna(),
        "missing_departure_time": df["departure_time"].isna(),
        "missing_arrival_time": df["arrival_time"].isna(),
        "missing_origin_airport": df["origin_airport_icao"].isna(),
        "missing_destination_airport": df["destination_airport_icao"].isna(),
        "invalid_airport_codes": ~df["origin_airport_icao"].fillna("").str.fullmatch(r"[A-Z0-9]{4}")
        | ~df["destination_airport_icao"].fillna("").str.fullmatch(r"[A-Z0-9]{4}"),
        "non_positive_flight_duration": df["arrival_time"] <= df["departure_time"],
    }

    combined_invalid = pd.Series(False, index=df.index)
    drop_rows = []
    for reason, mask in drop_masks.items():
        count = int(mask.sum())
        logger.info("Drop candidate rows for %s: %s", reason, count)
        combined_invalid |= mask.fillna(False)
        drop_rows.append({"reason": reason, "rows": count})

    cleaned = df.loc[~combined_invalid].copy()
    before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates(
        subset=[
            "icao24",
            "callsign",
            "departure_time",
            "arrival_time",
            "origin_airport_icao",
            "destination_airport_icao",
        ]
    )
    duplicates_dropped = before_dedup - len(cleaned)
    drop_rows.append({"reason": "duplicate_rows", "rows": duplicates_dropped})

    cleaned["flight_duration_minutes"] = (
        (cleaned["arrival_time"] - cleaned["departure_time"]).dt.total_seconds() / 60.0
    ).round(2)
    cleaned = cleaned.sort_values(["icao24", "departure_time", "arrival_time"]).reset_index(drop=True)

    logger.info("Flights rows: %s -> %s after cleaning.", initial_rows, len(cleaned))
    return cleaned, pd.DataFrame(drop_rows)


def clean_flights(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Run the cleaning pipeline for raw flights data."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    source = paths["raw_dir"] / config["sources"]["flights"]["raw_filename"]
    destination = paths["interim_dir"] / "flights_clean.parquet"

    if input_path:
        source = resolve_path(input_path, project_root)
    if output_path:
        destination = resolve_path(output_path, project_root)

    logger.info("Reading raw flights from %s", source)
    df = read_table(source)
    cleaned, drop_stats = clean_flights_df(df, logger)
    write_table(cleaned, destination)
    write_table(drop_stats, destination.with_name("flights_clean_drop_stats.csv"))
    logger.info("Clean flights saved to %s", destination)
    return cleaned


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom raw flights input.")
    parser.add_argument("--output-path", help="Optional custom cleaned output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    clean_flights(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
