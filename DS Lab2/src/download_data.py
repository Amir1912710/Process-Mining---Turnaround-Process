"""Download or copy reference datasets into data/raw."""

from __future__ import annotations

import argparse

from src.config import get_data_paths, get_project_root, load_config, resolve_path
from src.utils import is_url, materialize_source, setup_logging


REFERENCE_SOURCES = {
    "aircraft_metadata": "Aircraft metadata",
    "ourairports": "OurAirports airport reference",
    "openflights_airlines": "OpenFlights airlines reference",
    "openflights_airports": "OpenFlights airports reference",
}


def download_reference_data(config_path: str | None = None, overwrite: bool = False) -> None:
    """Download or copy reference files based on the provided configuration."""
    config = load_config(config_path)
    logger = setup_logging(config["logging"]["level"])
    project_root = get_project_root()
    paths = get_data_paths(config, project_root)
    raw_dir = paths["raw_dir"]

    for source_key, label in REFERENCE_SOURCES.items():
        source_cfg = config["sources"].get(source_key, {})
        source_value = source_cfg.get("local_path") or source_cfg.get("url")
        output_path = raw_dir / source_cfg.get("raw_filename", f"{source_key}.csv")

        if not source_value:
            logger.warning("Skipping %s because no source was configured.", label)
            continue

        if not is_url(str(source_value)):
            source_value = str(resolve_path(source_value, project_root))

        try:
            materialize_source(source_value, output_path, overwrite=overwrite, logger=logger)
        except Exception as exc:
            logger.warning("Failed to materialize %s: %s", label, exc)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default_config.yaml", help="Path to YAML/JSON config.")
    parser.add_argument("--overwrite", action="store_true", help="Force re-download or re-copy.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    download_reference_data(config_path=args.config, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
