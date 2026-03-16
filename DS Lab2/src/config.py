"""Configuration helpers for the turnaround data pipeline."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "raw_dir": "data/raw",
        "interim_dir": "data/interim",
        "processed_dir": "data/processed",
    },
    "sources": {
        "flights": {
            "local_path": "data/raw/sample_opensky_flights.csv",
            "url": None,
            "raw_filename": "opensky_flights_raw.csv",
        },
        "aircraft_metadata": {
            "local_path": None,
            "url": "https://opensky-network.org/datasets/metadata/aircraftDatabase.csv",
            "raw_filename": "opensky_aircraft_metadata.csv",
        },
        "ourairports": {
            "local_path": None,
            "url": "https://ourairports.com/data/airports.csv",
            "raw_filename": "ourairports_airports.csv",
        },
        "openflights_airlines": {
            "local_path": None,
            "url": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat",
            "raw_filename": "openflights_airlines.dat",
        },
        "openflights_airports": {
            "local_path": None,
            "url": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat",
            "raw_filename": "openflights_airports.dat",
        },
    },
    "processing": {
        "turnaround": {
            "min_minutes": 15,
            "max_minutes": 240,
        },
        "acdm": {
            "taxi_in_minutes": 7,
            "taxi_out_minutes": 12,
            "include_ground_handling_markers": False,
            "drop_invalid_milestones": True,
        },
    },
    "logging": {
        "level": "INFO",
    },
}


def get_project_root() -> Path:
    """Return the repository root based on this file location."""
    return Path(__file__).resolve().parents[1]


def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML or JSON config and merge it with defaults."""
    config = deepcopy(DEFAULT_CONFIG)
    if config_path is None:
        return config

    path = Path(config_path)
    if not path.is_absolute():
        path = get_project_root() / path

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() in {".yaml", ".yml"}:
            loaded = yaml.safe_load(handle) or {}
        elif path.suffix.lower() == ".json":
            loaded = json.load(handle)
        else:
            raise ValueError("Config file must be YAML or JSON.")

    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a mapping.")

    return _deep_update(config, loaded)


def resolve_path(path_value: str | Path, project_root: Path | None = None) -> Path:
    """Resolve a configured path relative to the project root."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    root = project_root or get_project_root()
    return root / path


def get_data_paths(config: dict[str, Any], project_root: Path | None = None) -> dict[str, Path]:
    """Return resolved raw/interim/processed directories."""
    root = project_root or get_project_root()
    return {
        "raw_dir": resolve_path(config["paths"]["raw_dir"], root),
        "interim_dir": resolve_path(config["paths"]["interim_dir"], root),
        "processed_dir": resolve_path(config["paths"]["processed_dir"], root),
    }
