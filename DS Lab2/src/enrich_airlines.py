"""Derive airline labels from callsigns using OpenFlights references when available."""

from __future__ import annotations

import argparse

import pandas as pd

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import prefer_existing_path, read_table, setup_logging, write_table


OPENFLIGHTS_AIRLINE_COLUMNS = [
    "airline_id",
    "name",
    "alias",
    "iata",
    "icao",
    "callsign",
    "country",
    "active",
]


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.is_unique:
        df = df.loc[:, ~df.columns.duplicated()].copy()
    return df


def _remove_existing_airline_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_columns = []
    for column in df.columns:
        if column in {"airline", "airline_country"} or column.startswith("airline_"):
            drop_columns.append(column)
    if drop_columns:
        df = df.drop(columns=drop_columns, errors="ignore")
    return df


def _normalize_airline_ref(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["iata"] = df["iata"].astype("string").str.strip().str.upper().replace({"\\N": pd.NA, "": pd.NA})
    df["icao"] = df["icao"].astype("string").str.strip().str.upper().replace({"\\N": pd.NA, "": pd.NA})
    df["name"] = df["name"].astype("string").str.strip().replace({"\\N": pd.NA, "": pd.NA})
    df["country"] = df["country"].astype("string").str.strip().replace({"\\N": pd.NA, "": pd.NA})
    return df


def derive_airline_candidates(callsign_series: pd.Series) -> pd.DataFrame:
    """Extract likely ICAO and IATA airline code prefixes from callsigns."""
    cleaned = callsign_series.astype("string").fillna("").str.upper().str.strip()
    alpha = cleaned.str.extract(r"^([A-Z]+)", expand=False).fillna("")
    return pd.DataFrame(
        {
            "airline_icao_candidate": alpha.str[:3].replace({"": pd.NA}),
            "airline_iata_candidate": alpha.str[:2].replace({"": pd.NA}),
        }
    )


def enrich_with_airlines(
    config_path: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Attach airline labels when an OpenFlights airline reference is available."""
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

    flights = _remove_existing_airline_columns(_deduplicate_columns(read_table(source)))
    reference_path = paths["raw_dir"] / config["sources"]["openflights_airlines"]["raw_filename"]

    empty_callsigns = pd.Series(index=flights.index, dtype="string")
    candidates = derive_airline_candidates(flights["callsign"] if "callsign" in flights.columns else empty_callsigns)
    flights = pd.concat([flights.reset_index(drop=True), candidates], axis=1)

    if not reference_path.exists():
        logger.warning("OpenFlights airline reference not found at %s. Writing flights through unchanged.", reference_path)
        if "airline" not in flights.columns:
            flights["airline"] = pd.NA
            flights["airline_country"] = pd.NA
        write_table(flights, destination)
        return flights

    airlines = read_table(reference_path, header=None, names=OPENFLIGHTS_AIRLINE_COLUMNS)
    airlines = _normalize_airline_ref(airlines)

    icao_ref = (
        airlines.dropna(subset=["icao"])
        .drop_duplicates(subset=["icao"])
        .rename(columns={"icao": "airline_icao_candidate", "name": "airline_name_icao", "country": "airline_country_icao"})
    )
    iata_ref = (
        airlines.dropna(subset=["iata"])
        .drop_duplicates(subset=["iata"])
        .rename(columns={"iata": "airline_iata_candidate", "name": "airline_name_iata", "country": "airline_country_iata"})
    )

    flights = flights.merge(
        icao_ref[["airline_icao_candidate", "airline_name_icao", "airline_country_icao"]],
        on="airline_icao_candidate",
        how="left",
    )
    flights = flights.merge(
        iata_ref[["airline_iata_candidate", "airline_name_iata", "airline_country_iata"]],
        on="airline_iata_candidate",
        how="left",
    )

    flights["airline"] = flights["airline_name_icao"].combine_first(flights["airline_name_iata"])
    flights["airline_country"] = flights["airline_country_icao"].combine_first(flights["airline_country_iata"])
    flights = flights.drop(
        columns=[
            "airline_name_icao",
            "airline_country_icao",
            "airline_name_iata",
            "airline_country_iata",
        ],
        errors="ignore",
    )
    flights = _deduplicate_columns(flights)

    missing_rate = float(flights["airline"].isna().mean()) if "airline" in flights.columns else 1.0
    logger.info("Airline missing rate: %.2f%%", missing_rate * 100)
    write_table(flights, destination)
    logger.info("Airline enrichment saved to %s", destination)
    return flights


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional custom flights input path.")
    parser.add_argument("--output-path", help="Optional custom enriched output path.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    enrich_with_airlines(config_path=args.config, input_path=args.input_path, output_path=args.output_path)


if __name__ == "__main__":
    main()
