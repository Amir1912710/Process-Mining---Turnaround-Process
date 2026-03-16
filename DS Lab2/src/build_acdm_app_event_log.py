"""Build a process-mining event log from A-CDM app milestone snapshots."""

from __future__ import annotations

import argparse

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import read_table, setup_logging, write_table


EVENT_COLUMNS = [
    ("TOBT", "tobt_utc", 1),
    ("EOBT", "eobt_utc", 2),
    ("TSAT", "tsat_utc", 3),
    ("CTOT", "ctot_utc", 4),
]


def build_acdm_app_event_log_df(df: pd.DataFrame) -> pd.DataFrame:
    """Build an event log from explicitly visible A-CDM milestone times."""
    events = []
    for activity, timestamp_col, default_order in EVENT_COLUMNS:
        if timestamp_col not in df.columns:
            continue
        events.append(
            pd.DataFrame(
                {
                    "case_id": df["case_id"],
                    "activity": activity,
                    "timestamp": df[timestamp_col],
                    "callsign": df["callsign"],
                    "flight_number": df["flight_number"],
                    "airport_icao": df["origin_airport_icao"],
                    "destination_airport_icao": df["destination_airport_icao"],
                    "airline": df.get("airline"),
                    "airline_segment": df.get("airline_segment"),
                    "aircraft_type": df.get("aircraft_type"),
                    "status": df.get("status"),
                    "gate": df.get("gate"),
                    "position": df.get("position"),
                    "runway": df.get("runway"),
                    "taxitime_minutes": df.get("taxitime_minutes"),
                    "sid": df.get("sid"),
                    "default_event_order": default_order,
                }
            )
        )

    if not events:
        return pd.DataFrame(columns=["case_id", "activity", "timestamp"])

    event_log = pd.concat(events, ignore_index=True)
    event_log = event_log.dropna(subset=["timestamp"]).copy()
    event_log = event_log.sort_values(["case_id", "timestamp", "default_event_order"]).reset_index(drop=True)
    event_log["event_order"] = event_log.groupby("case_id").cumcount() + 1
    event_log["ordered_ok"] = event_log.groupby("case_id")["timestamp"].transform(lambda series: series.is_monotonic_increasing)
    return event_log


def build_acdm_app_event_log(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Create an event log from normalized A-CDM app snapshot data."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    source = resolve_path(input_path, project_root) if input_path else paths["interim_dir"] / "acdm_app_snapshots.parquet"
    destination = resolve_path(output_path, project_root) if output_path else paths["processed_dir"] / "acdm_app_event_log.parquet"

    snapshots = read_table(source)
    event_log = build_acdm_app_event_log_df(snapshots)
    write_table(event_log.drop(columns=["ordered_ok"], errors="ignore"), destination)
    write_table(
        event_log.groupby("case_id")["ordered_ok"].max().reset_index(),
        destination.with_name("acdm_app_event_log_validation.csv"),
    )
    logger.info("A-CDM app event log saved to %s", destination)
    return event_log


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Input path for normalized A-CDM app snapshot data.")
    parser.add_argument("--output-path", help="Output path for A-CDM app event log.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    build_acdm_app_event_log(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
