"""Helpers for airline identity enrichment and segment classification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.config import get_project_root
from src.utils import normalise_callsign


DEFAULT_SEGMENT_CONFIG: dict[str, dict[str, list[str]]] = {
    "low_cost": {
        "names": [
            "Ryanair",
            "easyJet",
            "Wizz Air",
            "Southwest Airlines",
            "SunExpress",
            "Vueling Airlines",
            "Jet2.com",
            "Spirit Airlines",
            "Frontier Airlines",
            "Pegasus Airlines",
            "Norwegian Air Shuttle",
            "Transavia Airlines",
            "Eurowings",
            "Volotea",
            "Flydubai",
            "Jetstar Airways",
        ],
        "iata": ["FR", "U2", "W6", "WN", "XQ", "VY", "LS", "NK", "F9", "PC", "DY", "HV", "EW", "V7", "FZ", "JQ"],
        "icao": ["RYR", "EZY", "WZZ", "SWA", "SXS", "VLG", "EXS", "NKS", "FFT", "PGT", "NAX", "TRA", "EWG", "VOE", "FDB", "JST"],
    },
    "full_service": {
        "names": [
            "Lufthansa",
            "Swiss International Air Lines",
            "Austrian Airlines",
            "Brussels Airlines",
            "ITA Airways",
            "Air France",
            "airBaltic",
            "Air Serbia",
            "Discover Airlines",
            "Sichuan Airlines",
            "KLM Royal Dutch Airlines",
            "British Airways",
            "Iberia",
            "SAS",
            "Finnair",
            "Turkish Airlines",
            "Qatar Airways",
            "Emirates",
            "Etihad Airways",
            "Singapore Airlines",
            "Cathay Pacific",
            "ANA",
            "Japan Airlines",
            "Delta Air Lines",
            "United Airlines",
            "American Airlines",
            "Alaska Airlines",
            "Air Canada",
            "TAP Portugal",
            "LOT Polish Airlines",
            "Croatia Airlines",
            "Aegean Airlines",
            "Royal Air Maroc",
            "El Al",
            "Condor",
            "Cape Air",
            "SkyWest",
            "Republic Airlines",
        ],
        "iata": [
            "LH",
            "LX",
            "OS",
            "SN",
            "AZ",
            "AF",
            "BT",
            "JU",
            "4Y",
            "3U",
            "KL",
            "BA",
            "IB",
            "SK",
            "AY",
            "TK",
            "QR",
            "EK",
            "EY",
            "SQ",
            "CX",
            "NH",
            "JL",
            "DL",
            "UA",
            "AA",
            "AS",
            "AC",
            "TP",
            "LO",
            "OU",
            "A3",
            "AT",
            "LY",
            "DE",
            "9K",
            "OO",
            "YX",
        ],
        "icao": [
            "DLH",
            "SWR",
            "AUA",
            "BEL",
            "ITY",
            "AFR",
            "BTI",
            "ASL",
            "OCN",
            "CSC",
            "KLM",
            "BAW",
            "IBE",
            "SAS",
            "FIN",
            "THY",
            "QTR",
            "UAE",
            "ETD",
            "SIA",
            "CPA",
            "ANA",
            "JAL",
            "DAL",
            "UAL",
            "AAL",
            "ASA",
            "ACA",
            "TAP",
            "LOT",
            "CTN",
            "AEE",
            "RAM",
            "ELY",
            "CFG",
            "KAP",
            "SKW",
            "RPA",
        ],
    },
}

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


def _normalize_token(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if not text or text in {"\\N", "NAN", "NONE", "<NA>"}:
        return None
    return text


def load_airline_segment_config(config_path: str | Path | None = None) -> dict[str, dict[str, set[str]]]:
    """Load airline segment mapping from YAML and normalize it to sets."""
    if config_path is None:
        candidate = get_project_root() / "configs" / "airline_segments.yaml"
        config_data: dict[str, Any]
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                config_data = yaml.safe_load(handle) or {}
        else:
            config_data = DEFAULT_SEGMENT_CONFIG
    else:
        path = Path(config_path)
        if not path.is_absolute():
            path = get_project_root() / path
        with path.open("r", encoding="utf-8") as handle:
            config_data = yaml.safe_load(handle) or {}

    normalized: dict[str, dict[str, set[str]]] = {}
    for segment, rules in config_data.items():
        normalized[segment] = {
            "names": {_normalize_token(value) for value in rules.get("names", []) if _normalize_token(value)},
            "iata": {_normalize_token(value) for value in rules.get("iata", []) if _normalize_token(value)},
            "icao": {_normalize_token(value) for value in rules.get("icao", []) if _normalize_token(value)},
        }
    return normalized


def derive_airline_code_candidates(
    df: pd.DataFrame,
    callsign_col: str = "callsign",
    flight_number_col: str = "flight_number",
) -> pd.DataFrame:
    """Derive airline IATA/ICAO candidates from callsigns and flight numbers."""
    result = pd.DataFrame(index=df.index)

    if callsign_col in df.columns:
        callsign = normalise_callsign(df[callsign_col]).fillna("")
        alpha = callsign.str.extract(r"^([A-Z]+)", expand=False).fillna("")
        result["airline_icao_candidate"] = alpha.str[:3].replace({"": pd.NA})
    else:
        result["airline_icao_candidate"] = pd.Series(index=df.index, dtype="string")

    if flight_number_col in df.columns:
        flight_number = (
            df[flight_number_col]
            .astype("string")
            .fillna("")
            .str.strip()
            .str.upper()
            .str.extract(r"^([A-Z0-9]{2})", expand=False)
        )
        result["airline_iata_candidate"] = flight_number.replace({"": pd.NA})
    else:
        result["airline_iata_candidate"] = pd.Series(index=df.index, dtype="string")

    return result


def load_openflights_airlines(reference_path: Path) -> pd.DataFrame:
    """Load and normalize OpenFlights airline reference."""
    airlines = pd.read_csv(reference_path, header=None, names=OPENFLIGHTS_AIRLINE_COLUMNS)
    airlines["iata"] = airlines["iata"].map(_normalize_token)
    airlines["icao"] = airlines["icao"].map(_normalize_token)
    airlines["name"] = airlines["name"].astype("string").str.strip().replace({"\\N": pd.NA, "": pd.NA})
    airlines["country"] = airlines["country"].astype("string").str.strip().replace({"\\N": pd.NA, "": pd.NA})
    return airlines


def enrich_airline_names(
    df: pd.DataFrame,
    reference_path: Path | None,
    airline_col: str = "airline",
    iata_col: str = "airline_iata_code",
    icao_col: str = "airline_icao_code",
) -> pd.DataFrame:
    """Backfill airline names and countries from OpenFlights."""
    enriched = df.copy()
    if reference_path is None or not reference_path.exists():
        if airline_col not in enriched.columns:
            enriched[airline_col] = pd.Series(pd.NA, index=enriched.index, dtype="string")
        if "airline_country" not in enriched.columns:
            enriched["airline_country"] = pd.Series(pd.NA, index=enriched.index, dtype="string")
        return enriched

    airlines = load_openflights_airlines(reference_path)
    icao_ref = (
        airlines.dropna(subset=["icao"])
        .drop_duplicates(subset=["icao"])
        .rename(columns={"icao": icao_col, "name": "_airline_name_icao", "country": "_airline_country_icao"})
    )
    iata_ref = (
        airlines.dropna(subset=["iata"])
        .drop_duplicates(subset=["iata"])
        .rename(columns={"iata": iata_col, "name": "_airline_name_iata", "country": "_airline_country_iata"})
    )

    if icao_col in enriched.columns:
        enriched[icao_col] = enriched[icao_col].map(_normalize_token)
        enriched = enriched.merge(
            icao_ref[[icao_col, "_airline_name_icao", "_airline_country_icao"]],
            on=icao_col,
            how="left",
        )
    else:
        enriched["_airline_name_icao"] = pd.NA
        enriched["_airline_country_icao"] = pd.NA

    if iata_col in enriched.columns:
        enriched[iata_col] = enriched[iata_col].map(_normalize_token)
        enriched = enriched.merge(
            iata_ref[[iata_col, "_airline_name_iata", "_airline_country_iata"]],
            on=iata_col,
            how="left",
        )
    else:
        enriched["_airline_name_iata"] = pd.NA
        enriched["_airline_country_iata"] = pd.NA

    if airline_col not in enriched.columns:
        enriched[airline_col] = pd.Series(pd.NA, index=enriched.index, dtype="string")
    if "airline_country" not in enriched.columns:
        enriched["airline_country"] = pd.Series(pd.NA, index=enriched.index, dtype="string")

    enriched[airline_col] = (
        enriched[airline_col]
        .combine_first(enriched["_airline_name_icao"])
        .combine_first(enriched["_airline_name_iata"])
    )
    enriched["airline_country"] = (
        enriched.get("airline_country", pd.Series(index=enriched.index, dtype="string"))
        .combine_first(enriched["_airline_country_icao"])
        .combine_first(enriched["_airline_country_iata"])
    )
    enriched = enriched.drop(
        columns=[
            "_airline_name_icao",
            "_airline_country_icao",
            "_airline_name_iata",
            "_airline_country_iata",
        ],
        errors="ignore",
    )
    return enriched


def classify_airline_records(
    df: pd.DataFrame,
    segment_config_path: str | Path | None = None,
    airline_col: str = "airline",
    iata_col: str = "airline_iata_code",
    icao_col: str = "airline_icao_code",
    callsign_col: str = "callsign",
) -> pd.DataFrame:
    """Add airline segment labels using airline name, IATA, ICAO, and callsign."""
    config = load_airline_segment_config(segment_config_path)
    classified = df.copy()

    airline_name = (
        classified[airline_col].astype("string").str.strip().str.upper()
        if airline_col in classified.columns
        else pd.Series(index=classified.index, dtype="string")
    )
    iata = (
        classified[iata_col].map(_normalize_token)
        if iata_col in classified.columns
        else pd.Series(index=classified.index, dtype="string")
    )
    icao = (
        classified[icao_col].map(_normalize_token)
        if icao_col in classified.columns
        else pd.Series(index=classified.index, dtype="string")
    )
    callsign = (
        normalise_callsign(classified[callsign_col]).fillna("")
        if callsign_col in classified.columns
        else pd.Series(index=classified.index, dtype="string")
    )
    callsign_icao = callsign.str.extract(r"^([A-Z]{3})", expand=False)
    callsign_iata = callsign.str.extract(r"^([A-Z0-9]{2})", expand=False)

    segment = pd.Series("other", index=classified.index, dtype="string")
    match_source = pd.Series(pd.NA, index=classified.index, dtype="string")

    for segment_name, rules in config.items():
        name_mask = airline_name.isin(rules["names"])
        iata_mask = iata.isin(rules["iata"]) | callsign_iata.isin(rules["iata"])
        icao_mask = icao.isin(rules["icao"]) | callsign_icao.isin(rules["icao"])
        combined = name_mask | iata_mask | icao_mask

        segment = segment.mask(combined & (segment == "other"), segment_name)
        match_source = match_source.mask(combined & name_mask & match_source.isna(), "airline_name")
        match_source = match_source.mask(combined & iata_mask & match_source.isna(), "iata_or_callsign")
        match_source = match_source.mask(combined & icao_mask & match_source.isna(), "icao_or_callsign")

    classified["airline_segment"] = segment
    classified["airline_segment_match_source"] = match_source
    return classified
