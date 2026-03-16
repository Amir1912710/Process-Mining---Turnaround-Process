"""Export processed outputs to CSV and PM4Py-friendly event log formats."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import get_data_paths, load_config
from src.utils import read_table, setup_logging, write_table


def _write_with_fallback(df, primary_path: Path, logger) -> Path:
    """Write an export file, falling back when the primary file is locked."""
    try:
        write_table(df, primary_path)
        return primary_path
    except PermissionError:
        fallback_path = primary_path.with_name(f"{primary_path.stem}_latest{primary_path.suffix}")
        write_table(df, fallback_path)
        logger.warning(
            "Could not overwrite %s because it is open or locked. Wrote %s instead.",
            primary_path,
            fallback_path,
        )
        return fallback_path


def export_outputs(config_path: str | None = None) -> None:
    """Write CSV exports for turnaround cases and event log tables."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)

    turnaround = read_table(paths["processed_dir"] / "turnaround_cases.parquet")
    event_log = read_table(paths["processed_dir"] / "acdm_event_log.parquet")

    turnaround_csv = paths["processed_dir"] / "turnaround_cases.csv"
    event_csv = paths["processed_dir"] / "acdm_event_log.csv"
    xes_ready_csv = paths["processed_dir"] / "acdm_event_log_xes_ready.csv"

    turnaround_written = _write_with_fallback(turnaround, turnaround_csv, logger)
    event_written = _write_with_fallback(
        event_log.sort_values(["case_id", "event_order", "timestamp"]),
        event_csv,
        logger,
    )

    xes_ready = event_log.rename(
        columns={
            "case_id": "case:concept:name",
            "activity": "concept:name",
            "timestamp": "time:timestamp",
        }
    ).sort_values(["case:concept:name", "event_order", "time:timestamp"])
    xes_written = _write_with_fallback(xes_ready, xes_ready_csv, logger)

    logger.info("CSV outputs saved to %s, %s, and %s", turnaround_written, event_written, xes_written)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    export_outputs(config_path=args.config)


if __name__ == "__main__":
    main()
