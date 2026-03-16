"""Validate turnaround cases and the derived event log, then write a quality report."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import read_table, setup_logging, summarise_missing, write_table


def build_quality_report(
    turnaround: pd.DataFrame,
    event_log: pd.DataFrame,
    report_path: Path,
    metrics_path: Path,
    logger,
) -> None:
    """Create markdown and CSV quality summaries for downstream review."""
    expected_events = int(event_log.groupby("case_id")["activity"].size().median()) if not event_log.empty else 0
    events_per_case = event_log.groupby("case_id")["activity"].size().rename("event_count")
    invalid_event_count_cases = int((events_per_case != expected_events).sum()) if expected_events else 0

    ordering_check = (
        event_log.sort_values(["case_id", "event_order", "timestamp"])
        .groupby("case_id")["timestamp"]
        .apply(lambda timestamps: timestamps.is_monotonic_increasing)
        .rename("ordered")
    )
    ordering_failures = int((~ordering_check).sum()) if not ordering_check.empty else 0

    missing_summary = summarise_missing(
        turnaround,
        [
            "airline",
            "aircraft_type",
            "turnaround_airport_country",
            "turnaround_airport_latitude",
            "turnaround_airport_longitude",
        ],
    )

    turnaround_stats = turnaround["turnaround_minutes"].describe(percentiles=[0.25, 0.5, 0.75, 0.9]).round(2)

    metrics = pd.DataFrame(
        [
            {"metric": "turnaround_case_count", "value": int(turnaround["case_id"].nunique())},
            {"metric": "event_log_case_count", "value": int(event_log["case_id"].nunique())},
            {"metric": "event_row_count", "value": int(len(event_log))},
            {"metric": "median_events_per_case", "value": float(events_per_case.median()) if not events_per_case.empty else 0},
            {"metric": "cases_with_unexpected_event_count", "value": invalid_event_count_cases},
            {"metric": "cases_with_timestamp_order_failures", "value": ordering_failures},
            {
                "metric": "missing_airline_rate",
                "value": float(
                    missing_summary.loc[missing_summary["column"] == "airline", "missing_rate"].iloc[0]
                )
                if not missing_summary.empty
                else 0,
            },
            {
                "metric": "missing_aircraft_type_rate",
                "value": float(
                    missing_summary.loc[missing_summary["column"] == "aircraft_type", "missing_rate"].iloc[0]
                )
                if not missing_summary.empty
                else 0,
            },
        ]
    )
    write_table(metrics, metrics_path)

    lines = [
        "# Data Quality Report",
        "",
        "## Dataset Overview",
        f"- Turnaround cases: {int(turnaround['case_id'].nunique())}",
        f"- Event log cases: {int(event_log['case_id'].nunique())}",
        f"- Event rows: {int(len(event_log))}",
        "",
        "## Event Log Consistency",
        f"- Expected events per case (median observed): {expected_events}",
        f"- Cases with unexpected event counts: {invalid_event_count_cases}",
        f"- Cases with timestamp ordering failures: {ordering_failures}",
        "",
        "## Enrichment Completeness",
    ]

    for _, row in missing_summary.iterrows():
        lines.append(f"- {row['column']}: {int(row['missing_count'])} missing ({row['missing_rate']:.2%})")

    lines.extend(
        [
            "",
            "## Turnaround Duration Distribution (minutes)",
            f"- count: {turnaround_stats.get('count', 0)}",
            f"- mean: {turnaround_stats.get('mean', 0)}",
            f"- std: {turnaround_stats.get('std', 0)}",
            f"- min: {turnaround_stats.get('min', 0)}",
            f"- 25%: {turnaround_stats.get('25%', 0)}",
            f"- 50%: {turnaround_stats.get('50%', 0)}",
            f"- 75%: {turnaround_stats.get('75%', 0)}",
            f"- 90%: {turnaround_stats.get('90%', 0)}",
            f"- max: {turnaround_stats.get('max', 0)}",
            "",
            "## Notes",
            "- ALDT/AIBT/AOBT/ATOT are proxy milestones derived from OpenSky-style flight timestamps and configurable taxi assumptions.",
            "- Missing airline enrichment is expected when callsign prefixes do not match OpenFlights reference data.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Quality report saved to %s", report_path)


def validate_event_log(
    config_path: str | None = None,
    turnaround_path: str | None = None,
    event_log_path: str | None = None,
) -> None:
    """Validate processed outputs and write quality artifacts."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    paths = get_data_paths(config)
    project_root = get_project_root()

    turnaround_source = paths["processed_dir"] / "turnaround_cases.parquet"
    event_source = paths["processed_dir"] / "acdm_event_log.parquet"
    if turnaround_path:
        turnaround_source = resolve_path(turnaround_path, project_root)
    if event_log_path:
        event_source = resolve_path(event_log_path, project_root)

    turnaround = read_table(turnaround_source)
    event_log = read_table(event_source)
    build_quality_report(
        turnaround=turnaround,
        event_log=event_log,
        report_path=paths["processed_dir"] / "data_quality_report.md",
        metrics_path=paths["processed_dir"] / "data_quality_metrics.csv",
        logger=logger,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--turnaround-path", help="Optional custom turnaround cases path.")
    parser.add_argument("--event-log-path", help="Optional custom event log path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    validate_event_log(
        config_path=args.config,
        turnaround_path=args.turnaround_path,
        event_log_path=args.event_log_path,
    )


if __name__ == "__main__":
    main()
