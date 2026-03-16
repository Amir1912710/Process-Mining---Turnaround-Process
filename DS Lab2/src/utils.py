"""Shared utilities for the turnaround data pipeline."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests


LOGGER_NAME = "turnaround_pipeline"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure application logging once and return the package logger."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_url(value: str | None) -> bool:
    """Return True when the provided string looks like an HTTP(S) URL."""
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def normalise_icao24(series: pd.Series) -> pd.Series:
    """Normalize aircraft hex identifiers to lowercase strings."""
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    )


def normalise_airport_code(series: pd.Series) -> pd.Series:
    """Normalize airport ICAO identifiers to uppercase strings."""
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "\\N": pd.NA})
    )


def normalise_callsign(series: pd.Series) -> pd.Series:
    """Normalize callsigns by trimming and removing embedded spaces."""
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.replace(" ", "", regex=False)
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
    )


def parse_utc_datetime(series: pd.Series) -> pd.Series:
    """Parse timestamps into timezone-aware UTC datetimes."""
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_share = numeric.notna().mean() if len(series) else 0.0
    if numeric_share >= 0.8:
        non_null = numeric.dropna()
        if not non_null.empty:
            median_abs = non_null.abs().median()
            unit = "ms" if median_abs > 1e11 else "s"
            return pd.to_datetime(numeric, utc=True, errors="coerce", unit=unit)
    return pd.to_datetime(series, utc=True, errors="coerce")


def materialize_source(
    source: str | Path,
    destination: Path,
    overwrite: bool = False,
    timeout: int = 90,
    logger: logging.Logger | None = None,
) -> Path:
    """Copy or download a source file into the data/raw directory."""
    log = logger or logging.getLogger(LOGGER_NAME)
    ensure_directory(destination.parent)

    if destination.exists() and not overwrite:
        log.info("Using existing file: %s", destination)
        return destination

    source_str = str(source)
    if is_url(source_str):
        log.info("Downloading %s -> %s", source_str, destination)
        response = requests.get(source_str, timeout=timeout)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return destination

    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    if not source_path.exists():
        raise FileNotFoundError(f"Local source does not exist: {source_path}")

    log.info("Copying %s -> %s", source_path, destination)
    shutil.copy2(source_path, destination)
    return destination


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read CSV or Parquet files into pandas."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path, **kwargs)
    if suffix in {".csv", ".dat", ".txt"}:
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported file type for {path}")


def write_table(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """Write a DataFrame to CSV or Parquet based on the file extension."""
    ensure_directory(path.parent)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=index)
    elif suffix == ".csv":
        df.to_csv(path, index=index)
    else:
        raise ValueError(f"Unsupported output file type for {path}")
    return path


def prefer_existing_path(*paths: Path) -> Path:
    """Return the first existing path from a list."""
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("None of the candidate input paths exist.")


def summarise_missing(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return missing-value counts and rates for selected columns."""
    rows = []
    row_count = len(df)
    for column in columns:
        missing = int(df[column].isna().sum()) if column in df.columns else row_count
        rate = missing / row_count if row_count else 0.0
        rows.append({"column": column, "missing_count": missing, "missing_rate": rate})
    return pd.DataFrame(rows)
