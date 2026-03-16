"""Build an A-CDM-style event log from turnaround cases."""

from __future__ import annotations

import argparse

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import read_table, setup_logging, write_table


def compute_milestones(
    turnaround: pd.DataFrame,
    taxi_in_minutes: int,
    taxi_out_minutes: int,
    include_ground_handling_markers: bool,
) -> pd.DataFrame:
    """Create ordered milestone events for each turnaround case."""
    base = turnaround.copy()
    base["aldt"] = base["arrival_time"]
    base["aibt"] = base["arrival_time"] + pd.to_timedelta(taxi_in_minutes, unit="m")
    base["aobt"] = base["departure_time"] - pd.to_timedelta(taxi_out_minutes, unit="m")
    base["atot"] = base["departure_time"]
    base["milestone_valid"] = (
        (base["aldt"] <= base["aibt"]) & (base["aibt"] <= base["aobt"]) & (base["aobt"] <= base["atot"])
    )

    event_specs = [
        ("LANDING", "aldt", "AIRBORNE_TO_RUNWAY", 1),
        ("IN_BLOCK", "aibt", "RAMP", 2),
        ("OFF_BLOCK", "aobt", "RAMP", 3),
        ("TAKEOFF", "atot", "RUNWAY", 4),
    ]

    if include_ground_handling_markers:
        event_specs.insert(2, ("GROUND_HANDLING_START", "aibt", "GROUND_CREW", 2))
        event_specs.insert(4, ("GROUND_HANDLING_END", "aobt", "GROUND_CREW", 5))
        event_specs = [
            (activity, timestamp_col, resource, index + 1)
            for index, (activity, timestamp_col, resource, _) in enumerate(event_specs)
        ]

    events = []
    for activity, timestamp_col, resource, event_order in event_specs:
        events.append(
            pd.DataFrame(
                {
                    "case_id": base["case_id"],
                    "activity": activity,
                    "timestamp": base[timestamp_col],
                    "icao24": base["icao24"],
                    "airport_icao": base["airport_icao"],
                    "airline": base["airline"],
                    "aircraft_type": base["aircraft_type"],
                    "turnaround_minutes": base["turnaround_minutes"],
                    "resource_hint": resource,
                    "event_order": event_order,
                    "milestone_valid": base["milestone_valid"],
                }
            )
        )

    event_log = pd.concat(events, ignore_index=True)
    return event_log.sort_values(["case_id", "timestamp", "event_order"]).reset_index(drop=True)


def build_acdm_event_log(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Build and optionally filter the A-CDM-style event log."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    source = paths["processed_dir"] / "turnaround_cases.parquet"
    if input_path:
        source = resolve_path(input_path, project_root)

    destination = paths["processed_dir"] / "acdm_event_log.parquet"
    if output_path:
        destination = resolve_path(output_path, project_root)

    turnaround = read_table(source)
    acdm_cfg = config["processing"]["acdm"]
    event_log = compute_milestones(
        turnaround=turnaround,
        taxi_in_minutes=int(acdm_cfg["taxi_in_minutes"]),
        taxi_out_minutes=int(acdm_cfg["taxi_out_minutes"]),
        include_ground_handling_markers=bool(acdm_cfg.get("include_ground_handling_markers", False)),
    )

    invalid_cases = event_log.loc[~event_log["milestone_valid"], "case_id"].nunique()
    logger.info("Invalid milestone cases detected: %s", invalid_cases)

    if acdm_cfg.get("drop_invalid_milestones", True):
        valid_case_ids = event_log.loc[event_log["milestone_valid"], "case_id"].unique()
        event_log = event_log.loc[event_log["case_id"].isin(valid_case_ids)].drop(columns=["milestone_valid"])
        logger.info("Dropped invalid milestone cases from the event log.")
    else:
        event_log["milestone_issue"] = ~event_log["milestone_valid"]
        event_log = event_log.drop(columns=["milestone_valid"])

    write_table(event_log, destination)
    logger.info("A-CDM event log saved to %s", destination)
    return event_log


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom turnaround cases input path.")
    parser.add_argument("--output-path", help="Optional custom event log output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    build_acdm_event_log(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
