"""Enrich cleaned flights with aircraft metadata."""

from __future__ import annotations

import argparse
import re

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import normalise_icao24, prefer_existing_path, read_table, setup_logging, write_table


AIRCRAFT_COLUMN_CANDIDATES = {
    "icao24": ["icao24", "icao_24", "icao"],
    "registration": ["registration", "reg"],
    "manufacturer_name": ["manufacturername", "manufacturer_name", "manufacturer"],
    "model": ["model", "modelname"],
    "typecode": ["typecode", "aircraft_type", "type_code"],
    "operator": ["operator", "operatorname", "owner"],
}


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.is_unique:
        df = df.loc[:, ~df.columns.duplicated()].copy()
    return df


def _remove_existing_aircraft_columns(df: pd.DataFrame) -> pd.DataFrame:
    managed_prefix = "aircraft_"
    drop_columns = [column for column in df.columns if column.startswith(managed_prefix)]
    if drop_columns:
        df = df.drop(columns=drop_columns, errors="ignore")
    return df


def _rename_columns(df: pd.DataFrame, mapping: dict[str, list[str]]) -> pd.DataFrame:
    lookup = {column: re.sub(r"[^a-z0-9]", "", column.strip().lower()) for column in df.columns}
    rename_map: dict[str, str] = {}
    for target, candidates in mapping.items():
        canonical_candidates = {re.sub(r"[^a-z0-9]", "", candidate.strip().lower()) for candidate in candidates}
        for original, canonical in lookup.items():
            if canonical in canonical_candidates:
                rename_map[original] = target
                break
    return df.rename(columns=rename_map)


def enrich_with_aircraft(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Merge aircraft metadata onto the flights table."""
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

    destination = paths["interim_dir"] / "flights_enriched.parquet"
    if output_path:
        destination = resolve_path(output_path, project_root)

    metadata_path = paths["raw_dir"] / config["sources"]["aircraft_metadata"]["raw_filename"]
    flights = _remove_existing_aircraft_columns(_deduplicate_columns(read_table(source)))

    if not metadata_path.exists():
        logger.warning("Aircraft metadata not found at %s. Writing input through unchanged.", metadata_path)
        write_table(flights, destination)
        return flights

    metadata = read_table(metadata_path)
    metadata = _rename_columns(metadata, AIRCRAFT_COLUMN_CANDIDATES).copy()
    if "icao24" not in metadata.columns:
        raise ValueError("Aircraft metadata is missing an icao24 column.")

    metadata["icao24"] = normalise_icao24(metadata["icao24"])
    selected_columns = [
        column
        for column in ["icao24", "registration", "manufacturer_name", "model", "typecode", "operator"]
        if column in metadata.columns
    ]
    metadata = metadata[selected_columns].drop_duplicates(subset=["icao24"])

    enriched = flights.merge(metadata, on="icao24", how="left")
    enriched = enriched.rename(
        columns={
            "registration": "aircraft_registration",
            "manufacturer_name": "aircraft_manufacturer",
            "model": "aircraft_model",
            "typecode": "aircraft_type",
            "operator": "aircraft_operator",
        }
    )
    enriched = _deduplicate_columns(enriched)

    missing_rate = float(enriched["aircraft_type"].isna().mean()) if "aircraft_type" in enriched.columns else 1.0
    logger.info("Aircraft type missing rate: %.2f%%", missing_rate * 100)
    write_table(enriched, destination)
    logger.info("Aircraft enrichment saved to %s", destination)
    return enriched


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom flights input path.")
    parser.add_argument("--output-path", help="Optional custom enriched output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    enrich_with_aircraft(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
