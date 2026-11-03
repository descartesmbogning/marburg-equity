"""Shared paths, constants and helpers for the Marburg equity pipeline."""
from pathlib import Path
import re

import country_converter as coco
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"            # licensed / personal data, never committed
PROCESSED = ROOT / "data" / "processed"  # derived, shareable tables
REFERENCE = ROOT / "data" / "reference"  # hand-built lookup tables
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
for p in (PROCESSED, TABLES, FIGURES):
    p.mkdir(parents=True, exist_ok=True)

WOS_FILE = RAW / "woscc_bon_23_02_verif_on_wos.xls"
GENDER_FILE = RAW / "author_names_gender_2007.csv"

# Analysis window. WoS indexes funding acknowledgements systematically from 2008
# (Paul-Hus et al. 2016), and first names are reliable from 2007 onward.
YEAR_MIN = 2008
YEAR_MAX = 2023  # export date: 23 Feb 2023 (2023 is a partial year)

_cc = coco.CountryConverter()

# WoS address spellings that country_converter does not resolve on its own
_WOS_COUNTRY_FIXES = {
    "england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom",
    "north ireland": "United Kingdom", "northern ireland": "United Kingdom",
    "peoples r china": "China", "dem rep congo": "DR Congo", "rep congo": "Congo Republic",
    "u arab emirates": "United Arab Emirates", "cote ivoire": "Cote d'Ivoire",
    "turkiye": "Turkey", "papua n guinea": "Papua New Guinea", "trinid & tobago": "Trinidad and Tobago",
    "bosnia & herceg": "Bosnia and Herzegovina", "st kitts & nevi": "Saint Kitts and Nevis",
}


def norm_country(raw: str):
    """Map the last segment of a WoS address to a short English country name."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip().rstrip(".")
    if re.search(r"\bUSA$", s):
        return "United States"
    key = s.lower()
    if key in _WOS_COUNTRY_FIXES:
        return _WOS_COUNTRY_FIXES[key]
    name = _cc.convert(s, to="name_short", not_found=None)
    if isinstance(name, list):
        name = name[0] if name else None
    return name


def split_addresses(addresses: str):
    """Split a WoS 'Addresses' string into (author-name list, address text) pairs.

    Format: "[Last, First; Last2, First2] Org, Dept, City, Country; [..] Org2, ..."
    Addresses without a bracket get an empty author list.
    """
    out = []
    if not isinstance(addresses, str):
        return out
    for m in re.finditer(r"(?:\[([^\]]*)\]\s*)?([^;\[]+)", addresses):
        names, addr = m.group(1), m.group(2).strip()
        if not addr:
            continue
        who = [n.strip().lower() for n in names.split(";")] if names else []
        out.append((who, addr))
    return out


def org_of(addr: str) -> str:
    """First comma segment of a WoS address = the main organisation."""
    return addr.split(",")[0].strip().lower()


def country_of(addr: str):
    return norm_country(addr.split(",")[-1])


def save(df: pd.DataFrame, name: str, where: Path = TABLES, index=False):
    path = where / f"{name}.csv"
    df.to_csv(path, index=index)
    return path
