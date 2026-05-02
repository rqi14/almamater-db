"""Country/territory name -> ISO 3166-1 alpha-2."""
from __future__ import annotations

COUNTRY_ISO: dict[str, str] = {
    "China (Mainland)": "CN",
    "China": "CN",
    "Mainland China": "CN",
    "Hong Kong SAR": "HK",
    "Hong Kong": "HK",
    "Macau SAR": "MO",
    "Macau": "MO",
    "Taiwan": "TW",
    "United States": "US",
    "USA": "US",
    "United States of America": "US",
    "United Kingdom": "GB",
    "UK": "GB",
    "Australia": "AU",
    "Canada": "CA",
    "Germany": "DE",
    "France": "FR",
    "Switzerland": "CH",
    "Netherlands": "NL",
    "Singapore": "SG",
    "Japan": "JP",
    "South Korea": "KR",
    "Korea, South": "KR",
    "Republic of Korea": "KR",
    "Sweden": "SE",
    "Belgium": "BE",
    "Italy": "IT",
    "Spain": "ES",
    "Denmark": "DK",
    "Finland": "FI",
    "Norway": "NO",
    "Ireland": "IE",
    "New Zealand": "NZ",
    "Russia": "RU",
    "Russian Federation": "RU",
    "Brazil": "BR",
    "India": "IN",
    "Mexico": "MX",
    "Argentina": "AR",
    "Chile": "CL",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "Israel": "IL",
    "Turkey": "TR",
    "South Africa": "ZA",
    "Malaysia": "MY",
    "Thailand": "TH",
    "Indonesia": "ID",
    "Philippines": "PH",
    "Vietnam": "VN",
    "Pakistan": "PK",
    "Egypt": "EG",
    "Austria": "AT",
    "Portugal": "PT",
    "Greece": "GR",
    "Poland": "PL",
    "Czech Republic": "CZ",
    "Hungary": "HU",
    "Iceland": "IS",
    "Lebanon": "LB",
    "Qatar": "QA",
    "Kuwait": "KW",
    "Colombia": "CO",
    "Peru": "PE",
}


def to_iso(country: str) -> str:
    if not country:
        return "XX"
    s = country.strip()
    if s in COUNTRY_ISO:
        return COUNTRY_ISO[s]
    # Tolerant lookup, ignore case + trailing parens.
    low = s.lower()
    for k, v in COUNTRY_ISO.items():
        if k.lower() == low:
            return v
    return "XX"
