"""Build simulator-ready profile tables from turnaround and app milestone datasets."""

from __future__ import annotations

import argparse

import pandas as pd

from src.airline_segments import classify_airline_records, enrich_airline_names
from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import read_table, setup_logging, write_table


def build_simulator_inputs(
    config_path: str | None = None,
    turnaround_path: str | None = None,
    app_snapshot_path: str | None = None,
    segment_config_path: str | None = None,
) -> None:
    """Create aggregated profiles that can be consumed by a turnaround simulator."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()
    airline_reference_path = paths["raw_dir"] / config["sources"]["openflights_airlines"]["raw_filename"]

    turnaround_source = resolve_path(turnaround_path, project_root) if turnaround_path else paths["processed_dir"] / "turnaround_cases.parquet"
    turnaround = read_table(turnaround_source)
    turnaround = enrich_airline_names(
        turnaround,
        reference_path=airline_reference_path if airline_reference_path.exists() else None,
        airline_col="airline",
        iata_col="airline_iata_code",
        icao_col="airline_icao_code",
    )
    if "outbound_callsign" in turnaround.columns and "callsign" not in turnaround.columns:
        turnaround["callsign"] = turnaround["outbound_callsign"]
    turnaround = classify_airline_records(
        turnaround,
        segment_config_path=segment_config_path,
        airline_col="airline",
        iata_col="airline_iata_code",
        icao_col="airline_icao_code",
        callsign_col="callsign",
    )
    turnaround = turnaround.loc[turnaround["airline_segment"].isin(["low_cost", "full_service"])].copy()

    simulator_profiles = (
        turnaround.groupby(["airport_icao", "airline_segment", "aircraft_type"], dropna=False)
        .agg(
            case_count=("case_id", "nunique"),
            mean_turnaround_minutes=("turnaround_minutes", "mean"),
            std_turnaround_minutes=("turnaround_minutes", "std"),
            p50_turnaround_minutes=("turnaround_minutes", "median"),
            p90_turnaround_minutes=("turnaround_minutes", lambda x: x.quantile(0.9)),
        )
        .reset_index()
    )

    app_source = resolve_path(app_snapshot_path, project_root) if app_snapshot_path else paths["interim_dir"] / "acdm_app_snapshots.parquet"
    if app_source.exists():
        app_df = read_table(app_source)
        app_df = classify_airline_records(
            app_df,
            segment_config_path=segment_config_path,
            airline_col="airline",
            iata_col="airline_iata_code",
            icao_col="airline_icao_code",
            callsign_col="callsign",
        )
        app_df = app_df.loc[app_df["airline_segment"].isin(["low_cost", "full_service"])].copy()
        app_df["tsat_minus_tobt_minutes"] = (app_df["tsat_utc"] - app_df["tobt_utc"]).dt.total_seconds() / 60.0
        app_df["ctot_minus_tsat_minutes"] = (app_df["ctot_utc"] - app_df["tsat_utc"]).dt.total_seconds() / 60.0
        app_profiles = (
            app_df.groupby(["origin_airport_icao", "airline_segment"], dropna=False)
            .agg(
                app_case_count=("case_id", "nunique"),
                mean_taxitime_minutes=("taxitime_minutes", "mean"),
                mean_tsat_minus_tobt_minutes=("tsat_minus_tobt_minutes", "mean"),
                mean_ctot_minus_tsat_minutes=("ctot_minus_tsat_minutes", "mean"),
            )
            .reset_index()
            .rename(columns={"origin_airport_icao": "airport_icao"})
        )
        simulator_profiles = simulator_profiles.merge(
            app_profiles,
            on=["airport_icao", "airline_segment"],
            how="left",
        )

    simulator_profiles = simulator_profiles.round(2)
    write_table(simulator_profiles, paths["processed_dir"] / "simulator_turnaround_profiles.parquet")
    write_table(simulator_profiles, paths["processed_dir"] / "simulator_turnaround_profiles.csv")
    logger.info("Simulator profiles saved to %s", paths["processed_dir"] / "simulator_turnaround_profiles.parquet")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--turnaround-path", help="Optional custom turnaround cases input.")
    parser.add_argument("--app-snapshot-path", help="Optional normalized A-CDM app snapshot input.")
    parser.add_argument("--segment-config", default="configs/airline_segments.yaml", help="Airline segment mapping file.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    build_simulator_inputs(
        config_path=args.config,
        turnaround_path=args.turnaround_path,
        app_snapshot_path=args.app_snapshot_path,
        segment_config_path=args.segment_config,
    )


if __name__ == "__main__":
    main()
