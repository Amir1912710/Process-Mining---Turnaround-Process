"""Construct aircraft turnaround cases from enriched flight sequences."""

from __future__ import annotations

import argparse

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import prefer_existing_path, read_table, setup_logging, write_table


def build_turnaround_cases_df(df: pd.DataFrame, min_minutes: int, max_minutes: int | None, logger) -> pd.DataFrame:
    """Pair each arrival with the next departure of the same aircraft at the same airport."""
    flights = df.sort_values(["icao24", "departure_time", "arrival_time"]).reset_index(drop=True).copy()

    flights["next_departure_time"] = flights.groupby("icao24")["departure_time"].shift(-1)
    flights["next_callsign"] = flights.groupby("icao24")["callsign"].shift(-1)
    flights["next_origin_airport_icao"] = flights.groupby("icao24")["origin_airport_icao"].shift(-1)
    flights["next_destination_airport_icao"] = flights.groupby("icao24")["destination_airport_icao"].shift(-1)
    if "airline" in flights.columns:
        flights["next_airline"] = flights.groupby("icao24")["airline"].shift(-1)
    else:
        flights["airline"] = pd.NA
        flights["next_airline"] = pd.NA

    if "aircraft_type" not in flights.columns:
        flights["aircraft_type"] = pd.NA

    same_airport_mask = flights["destination_airport_icao"] == flights["next_origin_airport_icao"]
    flights = flights.loc[same_airport_mask].copy()

    flights["turnaround_minutes"] = (
        (flights["next_departure_time"] - flights["arrival_time"]).dt.total_seconds() / 60.0
    ).round(2)

    if max_minutes is not None:
        valid_duration = flights["turnaround_minutes"].between(min_minutes, max_minutes, inclusive="both")
    else:
        valid_duration = flights["turnaround_minutes"] >= min_minutes

    filtered = flights.loc[valid_duration].copy()
    logger.info("Turnaround candidate pairs after airport match: %s", len(flights))
    logger.info("Turnaround cases retained after duration filter: %s", len(filtered))

    filtered = filtered.reset_index(drop=True)
    filtered["case_id"] = filtered.apply(
        lambda row: f"TURN_{row['icao24']}_{row['destination_airport_icao']}_{row['arrival_time']:%Y%m%dT%H%M%SZ}_{row.name:06d}",
        axis=1,
    )

    turnaround = pd.DataFrame(
        {
            "case_id": filtered["case_id"],
            "icao24": filtered["icao24"],
            "inbound_callsign": filtered["callsign"],
            "outbound_callsign": filtered["next_callsign"],
            "airport_icao": filtered["destination_airport_icao"],
            "arrival_time": filtered["arrival_time"],
            "departure_time": filtered["next_departure_time"],
            "turnaround_minutes": filtered["turnaround_minutes"],
            "airline": filtered["next_airline"].combine_first(filtered["airline"]),
            "airline_country": filtered["airline_country"] if "airline_country" in filtered.columns else pd.NA,
            "aircraft_type": filtered["aircraft_type"],
            "aircraft_model": filtered["aircraft_model"] if "aircraft_model" in filtered.columns else pd.NA,
            "aircraft_manufacturer": filtered["aircraft_manufacturer"]
            if "aircraft_manufacturer" in filtered.columns
            else pd.NA,
            "origin_airport": filtered["origin_airport_icao"],
            "next_destination_airport": filtered["next_destination_airport_icao"],
            "turnaround_airport_name": filtered["destination_airport_name"]
            if "destination_airport_name" in filtered.columns
            else pd.NA,
            "turnaround_airport_country": filtered["destination_airport_country"]
            if "destination_airport_country" in filtered.columns
            else pd.NA,
            "turnaround_airport_latitude": filtered["destination_airport_latitude"]
            if "destination_airport_latitude" in filtered.columns
            else pd.NA,
            "turnaround_airport_longitude": filtered["destination_airport_longitude"]
            if "destination_airport_longitude" in filtered.columns
            else pd.NA,
        }
    )

    turnaround = turnaround.sort_values(["airport_icao", "arrival_time", "departure_time"]).reset_index(drop=True)
    return turnaround


def build_turnaround_cases(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Build the turnaround case table from enriched flights."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    source = prefer_existing_path(
        paths["interim_dir"] / "flights_enriched.parquet",
        paths["interim_dir"] / "flights_clean.parquet",
    )
    if input_path:
        source = resolve_path(input_path, project_root)

    destination = paths["processed_dir"] / "turnaround_cases.parquet"
    if output_path:
        destination = resolve_path(output_path, project_root)

    turnaround_cfg = config["processing"]["turnaround"]
    flights = read_table(source)
    turnaround = build_turnaround_cases_df(
        flights,
        min_minutes=int(turnaround_cfg["min_minutes"]),
        max_minutes=int(turnaround_cfg["max_minutes"]) if turnaround_cfg.get("max_minutes") is not None else None,
        logger=logger,
    )
    write_table(turnaround, destination)
    logger.info("Turnaround cases saved to %s", destination)
    return turnaround


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom flights input path.")
    parser.add_argument("--output-path", help="Optional custom turnaround output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    build_turnaround_cases(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
