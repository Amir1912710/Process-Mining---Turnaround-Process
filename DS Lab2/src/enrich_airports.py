"""Enrich cleaned flights with airport metadata."""

from __future__ import annotations

import argparse

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import normalise_airport_code, prefer_existing_path, read_table, setup_logging, write_table


OPENFLIGHTS_AIRPORT_COLUMNS = [
    "airport_id",
    "name",
    "city",
    "country",
    "iata",
    "icao",
    "latitude_deg",
    "longitude_deg",
    "altitude_ft",
    "utc_offset_hours",
    "dst",
    "tz_database_timezone",
    "type",
    "source",
]


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.is_unique:
        df = df.loc[:, ~df.columns.duplicated()].copy()
    return df


def _remove_existing_airport_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = {"origin_airport_icao", "destination_airport_icao"}
    drop_columns = []
    for column in df.columns:
        if column in keep:
            continue
        if column.startswith("origin_airport_") or column.startswith("destination_airport_"):
            drop_columns.append(column)
    if drop_columns:
        df = df.drop(columns=drop_columns, errors="ignore")
    return df


def load_airport_reference(paths, config, logger) -> pd.DataFrame:
    """Load airport reference from OurAirports, falling back to OpenFlights."""
    ourairports_path = paths["raw_dir"] / config["sources"]["ourairports"]["raw_filename"]
    openflights_path = paths["raw_dir"] / config["sources"]["openflights_airports"]["raw_filename"]

    if ourairports_path.exists():
        logger.info("Using OurAirports reference: %s", ourairports_path)
        airports = read_table(ourairports_path)
        required = {"ident", "name", "iso_country", "latitude_deg", "longitude_deg"}
        missing = required - set(airports.columns)
        if missing:
            raise ValueError(f"OurAirports reference is missing required columns: {sorted(missing)}")

        airports = airports.rename(
            columns={
                "ident": "airport_icao",
                "name": "airport_name",
                "iso_country": "airport_country",
                "municipality": "airport_city",
                "latitude_deg": "airport_latitude",
                "longitude_deg": "airport_longitude",
                "type": "airport_type",
            }
        )
        keep = [
            column
            for column in [
                "airport_icao",
                "airport_name",
                "airport_country",
                "airport_city",
                "airport_latitude",
                "airport_longitude",
                "airport_type",
            ]
            if column in airports.columns
        ]
        airports = airports[keep].copy()
    elif openflights_path.exists():
        logger.info("OurAirports file missing. Falling back to OpenFlights airports: %s", openflights_path)
        airports = read_table(openflights_path, header=None, names=OPENFLIGHTS_AIRPORT_COLUMNS)
        airports = airports.rename(
            columns={
                "icao": "airport_icao",
                "name": "airport_name",
                "country": "airport_country",
                "city": "airport_city",
                "latitude_deg": "airport_latitude",
                "longitude_deg": "airport_longitude",
                "type": "airport_type",
            }
        )
        airports = airports[
            [
                "airport_icao",
                "airport_name",
                "airport_country",
                "airport_city",
                "airport_latitude",
                "airport_longitude",
                "airport_type",
            ]
        ].copy()
    else:
        raise FileNotFoundError("No airport reference file found in data/raw.")

    airports["airport_icao"] = normalise_airport_code(airports["airport_icao"])
    airports = airports.dropna(subset=["airport_icao"]).drop_duplicates(subset=["airport_icao"])
    return airports


def enrich_with_airports(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Merge airport reference fields onto the flights table."""
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

    flights = _remove_existing_airport_columns(_deduplicate_columns(read_table(source)))
    try:
        airports = load_airport_reference(paths, config, logger)
    except FileNotFoundError as exc:
        logger.warning("%s Writing input through unchanged.", exc)
        write_table(flights, destination)
        return flights

    origin_ref = airports.add_prefix("origin_").rename(columns={"origin_airport_icao": "origin_airport_icao"})
    destination_ref = airports.add_prefix("destination_").rename(
        columns={"destination_airport_icao": "destination_airport_icao"}
    )

    enriched = flights.merge(origin_ref, on="origin_airport_icao", how="left")
    enriched = enriched.merge(destination_ref, on="destination_airport_icao", how="left")
    enriched = _deduplicate_columns(enriched)

    for side in ["origin", "destination"]:
        country_col = f"{side}_airport_country"
        missing_rate = enriched[country_col].isna().mean() if country_col in enriched.columns else 1.0
        logger.info("%s airport country missing rate: %.2f%%", side.title(), missing_rate * 100)

    write_table(enriched, destination)
    logger.info("Airport enrichment saved to %s", destination)
    return enriched


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom flights input path.")
    parser.add_argument("--output-path", help="Optional custom enriched output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    enrich_with_airports(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
