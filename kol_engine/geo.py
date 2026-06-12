"""Country + region detection from messy affiliation strings.

PubMed affiliations are free text and inconsistent ("..., Boston, MA 02115, USA",
"..., Electronic address: x@y.org", "..., 169856, Singapore"). Naively taking the
last comma-separated token gives postcodes and department names. Instead we scan
the whole string for known country names/aliases (and US state names), prefer the
match nearest the end (where the country usually sits), and fall back to "Unknown".
"""
from __future__ import annotations

import re

# canonical country -> regex alias patterns (lowercase, word-boundaried)
_COUNTRY_PATTERNS: dict[str, list[str]] = {
    "USA": [r"\busa\b", r"\bu\.s\.a\.?\b", r"\bunited states\b", r"\bu\.s\.\b"],
    "Canada": [r"\bcanada\b"],
    "UK": [r"\bunited kingdom\b", r"\bu\.k\.?\b", r"\bengland\b", r"\bscotland\b",
           r"\bwales\b", r"\bnorthern ireland\b"],
    "Ireland": [r"\bireland\b"],
    "France": [r"\bfrance\b"],
    "Germany": [r"\bgermany\b", r"\bdeutschland\b"],
    "Italy": [r"\bitaly\b", r"\bitalia\b"],
    "Spain": [r"\bspain\b", r"\bespa", r"\bespana\b"],
    "Portugal": [r"\bportugal\b"],
    "Netherlands": [r"\bnetherlands\b", r"\bthe netherlands\b"],
    "Belgium": [r"\bbelgium\b"],
    "Switzerland": [r"\bswitzerland\b"],
    "Austria": [r"\baustria\b"],
    "Sweden": [r"\bsweden\b"],
    "Norway": [r"\bnorway\b"],
    "Denmark": [r"\bdenmark\b"],
    "Finland": [r"\bfinland\b"],
    "Poland": [r"\bpoland\b"],
    "Greece": [r"\bgreece\b"],
    "Czech Republic": [r"\bczech\b"],
    "Hungary": [r"\bhungary\b"],
    "Romania": [r"\bromania\b"],
    "Russia": [r"\brussia\b", r"\brussian federation\b"],
    "Turkey": [r"\bturkey\b", r"\bt[uü]rkiye\b"],
    "Israel": [r"\bisrael\b"],
    "Saudi Arabia": [r"\bsaudi arabia\b", r"\bksa\b", r"\briyadh\b", r"\bjeddah\b"],
    "United Arab Emirates": [r"\bunited arab emirates\b", r"\buae\b", r"\babu dhabi\b",
                             r"\bdubai\b", r"\bsharjah\b"],
    "Qatar": [r"\bqatar\b", r"\bdoha\b"],
    "Kuwait": [r"\bkuwait\b"],
    "Bahrain": [r"\bbahrain\b"],
    "Oman": [r"\boman\b", r"\bmuscat\b"],
    "Lebanon": [r"\blebanon\b", r"\bbeirut\b"],
    "Jordan": [r"\bjordan\b", r"\bamman\b"],
    "Egypt": [r"\begypt\b", r"\bcairo\b"],
    "Iran": [r"\biran\b", r"\btehran\b"],
    "Iraq": [r"\biraq\b"],
    "China": [r"\bchina\b", r"\bp\.?r\.? china\b", r"\bbeijing\b", r"\bshanghai\b"],
    "Japan": [r"\bjapan\b"],
    "South Korea": [r"\bsouth korea\b", r"\brepublic of korea\b", r"\bkorea\b"],
    "India": [r"\bindia\b"],
    "Pakistan": [r"\bpakistan\b"],
    "Singapore": [r"\bsingapore\b"],
    "Taiwan": [r"\btaiwan\b"],
    "Hong Kong": [r"\bhong kong\b"],
    "Australia": [r"\baustralia\b"],
    "New Zealand": [r"\bnew zealand\b"],
    "Brazil": [r"\bbrazil\b", r"\bbrasil\b"],
    "Argentina": [r"\bargentina\b"],
    "Mexico": [r"\bmexico\b", r"\bm[eé]xico\b"],
    "Chile": [r"\bchile\b"],
    "Colombia": [r"\bcolombia\b"],
    "South Africa": [r"\bsouth africa\b"],
}
_COMPILED = {c: [re.compile(p) for p in pats] for c, pats in _COUNTRY_PATTERNS.items()}

# full US state names -> USA (excluding ambiguous "Georgia"/"Washington")
_US_STATES = ["alabama", "alaska", "arizona", "arkansas", "california", "colorado",
              "connecticut", "delaware", "florida", "hawaii", "idaho", "illinois",
              "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
              "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
              "missouri", "montana", "nebraska", "nevada", "new hampshire",
              "new jersey", "new mexico", "new york", "north carolina", "north dakota",
              "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
              "south carolina", "south dakota", "tennessee", "texas", "utah",
              "vermont", "virginia", "west virginia", "wisconsin", "wyoming"]
_US_STATE_RE = re.compile(r"\b(" + "|".join(_US_STATES) + r")\b")
_US_ZIP_STATE_RE = re.compile(r",\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?")  # ", MA 02115"

_REGION: dict[str, str] = {}
for c in ["USA", "Canada"]:
    _REGION[c] = "North America"
for c in ["UK", "Ireland", "France", "Germany", "Italy", "Spain", "Portugal",
          "Netherlands", "Belgium", "Switzerland", "Austria", "Sweden", "Norway",
          "Denmark", "Finland", "Poland", "Greece", "Czech Republic", "Hungary",
          "Romania", "Russia"]:
    _REGION[c] = "Europe"
for c in ["Turkey", "Israel", "Saudi Arabia", "United Arab Emirates", "Qatar",
          "Kuwait", "Bahrain", "Oman", "Lebanon", "Jordan", "Iran", "Iraq"]:
    _REGION[c] = "Middle East / GCC"
for c in ["China", "Japan", "South Korea", "India", "Pakistan", "Singapore",
          "Taiwan", "Hong Kong", "Australia", "New Zealand"]:
    _REGION[c] = "Asia-Pacific"
for c in ["Brazil", "Argentina", "Mexico", "Chile", "Colombia"]:
    _REGION[c] = "Latin America"
for c in ["Egypt", "South Africa"]:
    _REGION[c] = "Africa"

# GCC member states, for an optional finer flag
GCC = {"Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait", "Bahrain", "Oman"}


def detect_country(affiliation: str | float | None) -> str:
    """Return a canonical country, or 'Unknown' if none can be identified."""
    if not affiliation or not isinstance(affiliation, str):
        return "Unknown"
    text = affiliation.lower()
    best_country, best_pos = "Unknown", -1
    for country, patterns in _COMPILED.items():
        for pat in patterns:
            m = None
            for m in pat.finditer(text):
                pass  # keep the last match
            if m and m.start() > best_pos:
                best_pos, best_country = m.start(), country
    if best_country != "Unknown":
        return best_country
    # US fallbacks: explicit "ST 02115" pattern or a full state name
    if _US_ZIP_STATE_RE.search(affiliation) or _US_STATE_RE.search(text):
        return "USA"
    return "Unknown"


def country_to_region(country: str | float | None) -> str:
    if not country or not isinstance(country, str):
        return "Unknown"
    return _REGION.get(country, "Unknown")


# Display order for filters/charts
REGION_ORDER = ["North America", "Europe", "Middle East / GCC", "Asia-Pacific",
                "Latin America", "Africa", "Unknown"]
