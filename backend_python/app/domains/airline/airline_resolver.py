"""Airline name resolver for IATA codes.

Provides airline name lookups from IATA codes for display purposes.
"""

# Comprehensive airline IATA code to name mapping
# Source: Most common international airlines
AIRLINE_NAMES: dict[str, str] = {
    # Major US carriers
    "AA": "American Airlines",
    "UA": "United Airlines",
    "DL": "Delta Air Lines",
    "WN": "Southwest Airlines",
    "B6": "JetBlue Airways",
    "AS": "Alaska Airlines",
    "NK": "Spirit Airlines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    # European carriers
    "BA": "British Airways",
    "LH": "Lufthansa",
    "AF": "Air France",
    "KL": "KLM Royal Dutch Airlines",
    "IB": "Iberia",
    "AZ": "ITA Airways",
    "LX": "Swiss International Air Lines",
    "OS": "Austrian Airlines",
    "SN": "Brussels Airlines",
    "TP": "TAP Air Portugal",
    "SK": "Scandinavian Airlines",
    "AY": "Finnair",
    "FI": "Icelandair",
    "U2": "easyJet",
    "FR": "Ryanair",
    "VY": "Vueling Airlines",
    "W6": "Wizz Air",
    "EW": "Eurowings",
    "TO": "Transavia",
    "EI": "Aer Lingus",
    # Middle East carriers
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "EY": "Etihad Airways",
    "SV": "Saudi Arabian Airlines",
    "MS": "EgyptAir",
    "RJ": "Royal Jordanian",
    "WY": "Oman Air",
    "GF": "Gulf Air",
    "ME": "Middle East Airlines",
    "TK": "Turkish Airlines",
    # Asian carriers
    "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",
    "NH": "All Nippon Airways",
    "JL": "Japan Airlines",
    "KE": "Korean Air",
    "OZ": "Asiana Airlines",
    "TG": "Thai Airways",
    "MH": "Malaysia Airlines",
    "GA": "Garuda Indonesia",
    "PR": "Philippine Airlines",
    "AI": "Air India",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "9W": "Jet Airways",
    "CZ": "China Southern Airlines",
    "CA": "Air China",
    "MU": "China Eastern Airlines",
    "HU": "Hainan Airlines",
    "VN": "Vietnam Airlines",
    "BG": "Biman Bangladesh Airlines",
    # Canadian carriers
    "AC": "Air Canada",
    "WS": "WestJet",
    "PD": "Porter Airlines",
    # Latin American carriers
    "LA": "LATAM Airlines",
    "AR": "Aerolineas Argentinas",
    "AV": "Avianca",
    "CM": "Copa Airlines",
    "AM": "Aeromexico",
    "VB": "VivaAerobus",
    "Y4": "Volaris",
    "G3": "Gol Transportes Aéreos",
    "AD": "Azul Brazilian Airlines",
    # African carriers
    "SA": "South African Airways",
    "ET": "Ethiopian Airlines",
    "KQ": "Kenya Airways",
    "AT": "Royal Air Maroc",
    "UU": "Air Austral",
    # Oceania carriers
    "QF": "Qantas",
    "VA": "Virgin Australia",
    "NZ": "Air New Zealand",
    "FJ": "Fiji Airways",
    # Low-cost carriers
    "4U": "Germanwings",
    "VX": "Virgin America",
    "DY": "Norwegian Air Shuttle",
    "PC": "Pegasus Airlines",
    "HV": "Transavia Netherlands",
    "TB": "TUIfly",
    # Cargo carriers (in case they appear)
    "FX": "FedEx Express",
    "5X": "UPS Airlines",
    "CK": "Cargolux",
}


def get_airline_name(iata_code: str) -> str | None:
    """Get airline name from IATA code.

    Args:
        iata_code: 2-letter IATA airline code (e.g., 'BA', 'AA')

    Returns:
        Airline name if found, None otherwise
    """
    if not iata_code:
        return None

    return AIRLINE_NAMES.get(iata_code.upper())


def get_airline_display_name(iata_code: str) -> str:
    """Get airline name with fallback to code if not found.

    Args:
        iata_code: 2-letter IATA airline code

    Returns:
        Airline name or formatted code (e.g., 'British Airways' or 'Airline BA')
    """
    if not iata_code:
        return "Unknown Airline"

    name = get_airline_name(iata_code)
    return name if name else f"Airline {iata_code.upper()}"
