"""Load a local or remote OpenSky-like flights CSV into data/raw."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import is_url, materialize_source, setup_logging


def ingest_flights(
    config_path: str | None = None,
    input_path: str | None = None,
    input_url: str | None = None,
    output_filename: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Copy or download the flights file into the configured raw directory."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    project_root = get_project_root()
    raw_dir = get_data_paths(config, project_root)["raw_dir"]

    source_cfg = config["sources"]["flights"]
    source_value = input_path or input_url or source_cfg.get("local_path") or source_cfg.get("url")
    if not source_value:
        raise ValueError(
            "No flights source configured. Provide --input-path, --input-url, or set sources.flights in the config."
        )

    if not is_url(str(source_value)):
        source_value = str(resolve_path(source_value, project_root))

    filename = output_filename or source_cfg.get("raw_filename", "opensky_flights_raw.csv")
    destination = raw_dir / filename
    materialize_source(source_value, destination, overwrite=overwrite, logger=logger)
    logger.info("Flights data ready at %s", destination)
    return destination


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--input-path", help="Optional local CSV path to an OpenSky-like flights export.")
    parser.add_argument("--input-url", help="Optional URL to a flights CSV.")
    parser.add_argument("--output-filename", help="Filename to use inside data/raw.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the raw destination file.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    ingest_flights(
        config_path=args.config,
        input_path=args.input_path,
        input_url=args.input_url,
        output_filename=args.output_filename,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
