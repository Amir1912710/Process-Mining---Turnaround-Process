"""Compare low-cost and full-service airline behaviour in processed datasets."""

from __future__ import annotations

import argparse

import pandas as pd

from src.airline_segments import classify_airline_records, enrich_airline_names
from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import read_table, setup_logging


def _to_markdown_table(df: pd.DataFrame) -> str:
    """Render a simple markdown table without optional dependencies."""
    if df.empty:
        return "No rows."

    render = df.copy()
    render = render.fillna("")
    headers = [str(column) for column in render.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in render.iterrows():
        lines.append("| " + " | ".join(str(value) for value in row.tolist()) + " |")
    return "\n".join(lines)


def _segment_summary(turnaround: pd.DataFrame) -> pd.DataFrame:
    subset = turnaround.loc[turnaround["airline_segment"].isin(["low_cost", "full_service"])].copy()
    if subset.empty:
        return pd.DataFrame()

    return (
        subset.groupby("airline_segment")
        .agg(
            cases=("case_id", "nunique"),
            unique_airlines=("airline", "nunique"),
            mean_turnaround_minutes=("turnaround_minutes", "mean"),
            median_turnaround_minutes=("turnaround_minutes", "median"),
            p90_turnaround_minutes=("turnaround_minutes", lambda x: x.quantile(0.9)),
            unique_airports=("airport_icao", "nunique"),
        )
        .reset_index()
        .round(2)
    )


def _app_summary(app_df: pd.DataFrame) -> pd.DataFrame:
    if app_df.empty or "airline_segment" not in app_df.columns:
        return pd.DataFrame()

    subset = app_df.loc[app_df["airline_segment"].isin(["low_cost", "full_service"])].copy()
    if subset.empty:
        return pd.DataFrame()

    subset["tsat_minus_tobt_minutes"] = (subset["tsat_utc"] - subset["tobt_utc"]).dt.total_seconds() / 60.0
    subset["ctot_minus_tsat_minutes"] = (subset["ctot_utc"] - subset["tsat_utc"]).dt.total_seconds() / 60.0
    subset["eobt_minus_tobt_minutes"] = (subset["eobt_utc"] - subset["tobt_utc"]).dt.total_seconds() / 60.0

    return (
        subset.groupby("airline_segment")
        .agg(
            flights=("case_id", "nunique"),
            mean_taxitime_minutes=("taxitime_minutes", "mean"),
            mean_tsat_minus_tobt_minutes=("tsat_minus_tobt_minutes", "mean"),
            mean_ctot_minus_tsat_minutes=("ctot_minus_tsat_minutes", "mean"),
            mean_eobt_minus_tobt_minutes=("eobt_minus_tobt_minutes", "mean"),
        )
        .reset_index()
        .round(2)
    )


def _build_highlights(turnaround_summary: pd.DataFrame, app_summary: pd.DataFrame) -> list[str]:
    highlights: list[str] = []
    if not turnaround_summary.empty and {"low_cost", "full_service"} <= set(turnaround_summary["airline_segment"]):
        low = turnaround_summary.loc[turnaround_summary["airline_segment"] == "low_cost"].iloc[0]
        full = turnaround_summary.loc[turnaround_summary["airline_segment"] == "full_service"].iloc[0]
        diff_mean = float(low["mean_turnaround_minutes"] - full["mean_turnaround_minutes"])
        faster_segment = "Low-cost" if diff_mean < 0 else "Full-service"
        highlights.append(
            f"{faster_segment} carriers show the shorter mean turnaround in the current turnaround dataset by {abs(diff_mean):.2f} minutes."
        )
        diff_p90 = float(low["p90_turnaround_minutes"] - full["p90_turnaround_minutes"])
        wider_segment = "Low-cost" if diff_p90 > 0 else "Full-service"
        highlights.append(
            f"{wider_segment} carriers show the larger 90th percentile turnaround by {abs(diff_p90):.2f} minutes."
        )

    if not app_summary.empty and {"low_cost", "full_service"} <= set(app_summary["airline_segment"]):
        low = app_summary.loc[app_summary["airline_segment"] == "low_cost"].iloc[0]
        full = app_summary.loc[app_summary["airline_segment"] == "full_service"].iloc[0]
        if pd.notna(low["mean_taxitime_minutes"]) and pd.notna(full["mean_taxitime_minutes"]):
            diff_taxi = float(low["mean_taxitime_minutes"] - full["mean_taxitime_minutes"])
            direction = "higher" if diff_taxi > 0 else "lower"
            highlights.append(
                f"Low-cost carriers show {direction} average app-reported taxi time by {abs(diff_taxi):.2f} minutes."
            )
    elif not app_summary.empty:
        highlights.append("A-CDM app sample is currently too small to compare low-cost and full-service groups robustly.")
    else:
        highlights.append("No normalized A-CDM app snapshot dataset was available for milestone-level segment comparison.")

    return highlights


def compare_airline_segments(
    config_path: str | None = None,
    turnaround_path: str | None = None,
    app_snapshot_path: str | None = None,
    segment_config_path: str | None = None,
) -> None:
    """Generate markdown and CSV comparison outputs for airline business-model segments."""
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

    app_summary = pd.DataFrame()
    app_top_routes = pd.DataFrame()
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
        app_summary = _app_summary(app_df)
        app_top_routes = (
            app_df.loc[app_df["airline_segment"].isin(["low_cost", "full_service"])]
            .assign(route=lambda frame: frame["origin_airport_icao"] + " -> " + frame["destination_airport_icao"])
            .groupby(["airline_segment", "route"])
            .size()
            .reset_index(name="flights")
            .sort_values(["airline_segment", "flights"], ascending=[True, False])
            .groupby("airline_segment")
            .head(5)
        )

    turnaround_summary = _segment_summary(turnaround)
    turnaround_top_airports = (
        turnaround.loc[turnaround["airline_segment"].isin(["low_cost", "full_service"])]
        .groupby(["airline_segment", "airport_icao"])
        .size()
        .reset_index(name="cases")
        .sort_values(["airline_segment", "cases"], ascending=[True, False])
        .groupby("airline_segment")
        .head(10)
    )
    highlights = _build_highlights(turnaround_summary, app_summary)

    turnaround_summary.to_csv(paths["processed_dir"] / "airline_segment_turnaround_summary.csv", index=False)
    turnaround_top_airports.to_csv(paths["processed_dir"] / "airline_segment_top_airports.csv", index=False)
    if not app_summary.empty:
        app_summary.to_csv(paths["processed_dir"] / "airline_segment_app_summary.csv", index=False)
    if not app_top_routes.empty:
        app_top_routes.to_csv(paths["processed_dir"] / "airline_segment_app_top_routes.csv", index=False)

    lines = [
        "# Airline Segment Comparison",
        "",
        "This report compares low-cost and full-service carriers using the processed turnaround dataset and, when available, the manually captured A-CDM app snapshot dataset.",
        "",
        "## Highlights",
    ]
    lines.extend([f"- {line}" for line in highlights])
    lines.extend(
        [
            "",
            "## Turnaround Summary",
            _to_markdown_table(turnaround_summary) if not turnaround_summary.empty else "No turnaround summary available.",
            "",
            "## Top Turnaround Airports",
            _to_markdown_table(turnaround_top_airports) if not turnaround_top_airports.empty else "No top-airport summary available.",
        ]
    )
    if not app_summary.empty:
        lines.extend(["", "## A-CDM App Milestone Summary", _to_markdown_table(app_summary)])
    if not app_top_routes.empty:
        lines.extend(["", "## A-CDM App Top Routes", _to_markdown_table(app_top_routes)])

    report_path = paths["processed_dir"] / "airline_segment_comparison.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Airline segment comparison saved to %s", report_path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--turnaround-path", help="Optional custom turnaround cases input.")
    parser.add_argument("--app-snapshot-path", help="Optional normalized A-CDM app snapshot input.")
    parser.add_argument("--segment-config", default="configs/airline_segments.yaml", help="Airline segment mapping file.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    compare_airline_segments(
        config_path=args.config,
        turnaround_path=args.turnaround_path,
        app_snapshot_path=args.app_snapshot_path,
        segment_config_path=args.segment_config,
    )


if __name__ == "__main__":
    main()
