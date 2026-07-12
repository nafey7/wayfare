"""Static country → tourist-hub map used by the itinerary side-searches (#1127, #1152).

When the user names a country instead of a city ("Montenegro", "Iceland"),
the FlightLogic flight + hotel APIs both require a real city — they reject
country-only inputs or, worse, the airport resolver fuzzy-matches the
country name to an unrelated airport in another country (in dev,
"Montenegro" was resolving to QGF in Brazil).

This module owns the deterministic mapping from country → list of tourist
hubs, each hub as ``(city, iata)``. The picks are *tourist hubs*, NOT
capitals — Brazil ranks Rio over Brasília, Australia ranks Sydney over
Canberra. Capitals are chosen only when they double as the country's
primary tourist destination (Tokyo, Bangkok, Paris).

Each country lists hubs in **priority order** (first = primary hub, used
for backward-compat single-hub callers and as the session anchor for
booking flows). Multi-hub entries (#1152) enable parallel flight + hotel
searches so the user sees options across all major gateways without having
to specify a city.

Keys are lowercase; the lookup helper normalises common articles ("the
US" → "us", "the UK" → "uk") before checking. The table intentionally
includes the **common informal abbreviations users actually type** ("uk",
"us", "uae", "usa").

Long-tail misses (rare or obscure countries not in this table) return
``None`` from :func:`lookup_country_tourist_hubs`; the caller then falls
through and the side-searches skip silently — same observable as the
country case pre-fix, no regression.
"""

from __future__ import annotations

from typing import Final

# Each entry: country (lowercase) →
#   (display_name, [(city, iata), ...])
# Hubs are in priority order: first = primary (used for backward-compat
# single-hub callers). Multi-hub countries list all major tourist gateways.
_COUNTRY_TOURIST_HUBS: Final[dict[str, tuple[str, list[tuple[str, str]]]]] = {
    # ----- Europe — small / single-gateway countries -----
    "montenegro": ("Montenegro", [("Kotor", "TIV"), ("Podgorica", "TGD")]),
    "iceland": ("Iceland", [("Reykjavik", "KEF")]),
    "ireland": ("Ireland", [("Dublin", "DUB"), ("Cork", "ORK")]),
    "portugal": ("Portugal", [("Lisbon", "LIS"), ("Porto", "OPO"), ("Faro", "FAO")]),
    "netherlands": ("Netherlands", [("Amsterdam", "AMS"), ("Rotterdam", "RTM")]),
    "belgium": ("Belgium", [("Brussels", "BRU"), ("Antwerp", "ANR")]),
    "switzerland": (
        "Switzerland",
        [("Zurich", "ZRH"), ("Geneva", "GVA"), ("Basel", "BSL")],
    ),
    "austria": (
        "Austria",
        [("Vienna", "VIE"), ("Salzburg", "SZG"), ("Innsbruck", "INN")],
    ),
    "czechia": ("Czechia", [("Prague", "PRG")]),
    "czech republic": ("Czech Republic", [("Prague", "PRG"), ("Brno", "BRQ")]),
    "hungary": ("Hungary", [("Budapest", "BUD"), ("Debrecen", "DEB")]),
    "poland": ("Poland", [("Krakow", "KRK"), ("Warsaw", "WAW"), ("Gdansk", "GDN")]),
    "croatia": ("Croatia", [("Split", "SPU"), ("Dubrovnik", "DBV"), ("Zagreb", "ZAG")]),
    "slovenia": ("Slovenia", [("Ljubljana", "LJU")]),
    "greece": (
        "Greece",
        [("Athens", "ATH"), ("Heraklion", "HER"), ("Thessaloniki", "SKG")],
    ),
    "albania": ("Albania", [("Tirana", "TIA")]),
    "bulgaria": ("Bulgaria", [("Sofia", "SOF"), ("Varna", "VAR"), ("Burgas", "BOJ")]),
    "romania": ("Romania", [("Bucharest", "OTP"), ("Cluj-Napoca", "CLJ")]),
    "serbia": ("Serbia", [("Belgrade", "BEG")]),
    "finland": ("Finland", [("Helsinki", "HEL"), ("Tampere", "TMP"), ("Turku", "TKU")]),
    "denmark": ("Denmark", [("Copenhagen", "CPH"), ("Aarhus", "AAR")]),
    "norway": ("Norway", [("Oslo", "OSL"), ("Bergen", "BGO"), ("Trondheim", "TRD")]),
    "sweden": (
        "Sweden",
        [("Stockholm", "ARN"), ("Gothenburg", "GOT"), ("Malmö", "MMX")],
    ),
    "estonia": ("Estonia", [("Tallinn", "TLL")]),
    "latvia": ("Latvia", [("Riga", "RIX")]),
    "lithuania": ("Lithuania", [("Vilnius", "VNO"), ("Kaunas", "KUN")]),
    "malta": ("Malta", [("Valletta", "MLA")]),
    "cyprus": ("Cyprus", [("Larnaca", "LCA"), ("Paphos", "PFO")]),
    "luxembourg": ("Luxembourg", [("Luxembourg", "LUX")]),
    "ukraine": ("Ukraine", [("Kyiv", "KBP"), ("Lviv", "LWO"), ("Odesa", "ODS")]),
    "russia": (
        "Russia",
        [("Moscow", "SVO"), ("St. Petersburg", "LED"), ("Sochi", "AER")],
    ),
    "belarus": ("Belarus", [("Minsk", "MSQ")]),
    "georgia": ("Georgia", [("Tbilisi", "TBS"), ("Batumi", "BUS")]),
    "armenia": ("Armenia", [("Yerevan", "EVN")]),
    "azerbaijan": ("Azerbaijan", [("Baku", "GYD")]),
    "kazakhstan": ("Kazakhstan", [("Almaty", "ALA"), ("Astana", "TSE")]),
    "uzbekistan": ("Uzbekistan", [("Tashkent", "TAS"), ("Samarkand", "SKD")]),
    "kyrgyzstan": ("Kyrgyzstan", [("Bishkek", "FRU")]),
    "tajikistan": ("Tajikistan", [("Dushanbe", "DYU")]),
    "turkmenistan": ("Turkmenistan", [("Ashgabat", "ASB")]),
    "mongolia": ("Mongolia", [("Ulaanbaatar", "ULN")]),
    "myanmar": ("Myanmar", [("Yangon", "RGN"), ("Mandalay", "MDL")]),
    "burma": ("Myanmar", [("Yangon", "RGN"), ("Mandalay", "MDL")]),
    # ----- Europe — large multi-hub countries -----
    "united kingdom": (
        "United Kingdom",
        [
            ("London", "LHR"),
            ("Edinburgh", "EDI"),
            ("Manchester", "MAN"),
            ("Birmingham", "BHX"),
        ],
    ),
    "uk": (
        "United Kingdom",
        [("London", "LHR"), ("Edinburgh", "EDI"), ("Manchester", "MAN")],
    ),
    "great britain": (
        "United Kingdom",
        [("London", "LHR"), ("Edinburgh", "EDI"), ("Manchester", "MAN")],
    ),
    "england": (
        "United Kingdom",
        [("London", "LHR"), ("Manchester", "MAN"), ("Birmingham", "BHX")],
    ),
    "scotland": ("United Kingdom", [("Edinburgh", "EDI"), ("Glasgow", "GLA")]),
    "germany": (
        "Germany",
        [
            ("Berlin", "BER"),
            ("Munich", "MUC"),
            ("Frankfurt", "FRA"),
            ("Hamburg", "HAM"),
        ],
    ),
    "france": (
        "France",
        [("Paris", "CDG"), ("Nice", "NCE"), ("Lyon", "LYS"), ("Marseille", "MRS")],
    ),
    "italy": (
        "Italy",
        [
            ("Rome", "FCO"),
            ("Milan", "MXP"),
            ("Venice", "VCE"),
            ("Florence", "FLR"),
            ("Naples", "NAP"),
        ],
    ),
    "spain": (
        "Spain",
        [
            ("Barcelona", "BCN"),
            ("Madrid", "MAD"),
            ("Malaga", "AGP"),
            ("Seville", "SVQ"),
            ("Ibiza", "IBZ"),
        ],
    ),
    # ----- Asia -----
    "japan": (
        "Japan",
        [("Tokyo", "HND"), ("Osaka", "KIX"), ("Fukuoka", "FUK"), ("Sapporo", "CTS")],
    ),
    "thailand": (
        "Thailand",
        [
            ("Bangkok", "BKK"),
            ("Chiang Mai", "CNX"),
            ("Phuket", "HKT"),
            ("Koh Samui", "USM"),
        ],
    ),
    "vietnam": (
        "Vietnam",
        [("Hanoi", "HAN"), ("Ho Chi Minh City", "SGN"), ("Da Nang", "DAD")],
    ),
    "indonesia": (
        "Indonesia",
        [("Denpasar", "DPS"), ("Jakarta", "CGK"), ("Lombok", "LOP")],
    ),
    "cambodia": ("Cambodia", [("Siem Reap", "REP"), ("Phnom Penh", "PNH")]),
    "laos": ("Laos", [("Vientiane", "VTE"), ("Luang Prabang", "LPQ")]),
    "south korea": (
        "South Korea",
        [("Seoul", "ICN"), ("Busan", "PUS"), ("Jeju", "CJU")],
    ),
    "korea": ("South Korea", [("Seoul", "ICN"), ("Busan", "PUS"), ("Jeju", "CJU")]),
    "taiwan": ("Taiwan", [("Taipei", "TPE"), ("Kaohsiung", "KHH")]),
    "philippines": (
        "Philippines",
        [("Manila", "MNL"), ("Cebu", "CEB"), ("Palawan", "PPS")],
    ),
    "malaysia": (
        "Malaysia",
        [("Kuala Lumpur", "KUL"), ("Penang", "PEN"), ("Kota Kinabalu", "BKI")],
    ),
    "singapore": ("Singapore", [("Singapore", "SIN")]),
    "sri lanka": ("Sri Lanka", [("Colombo", "CMB"), ("Mattala", "HRI")]),
    "nepal": ("Nepal", [("Kathmandu", "KTM"), ("Pokhara", "PKR")]),
    "bhutan": ("Bhutan", [("Paro", "PBH")]),
    "maldives": ("Maldives", [("Malé", "MLE")]),
    "india": (
        "India",
        [
            ("Delhi", "DEL"),
            ("Mumbai", "BOM"),
            ("Goa", "GOI"),
            ("Bangalore", "BLR"),
            ("Jaipur", "JAI"),
        ],
    ),
    "pakistan": (
        "Pakistan",
        [("Karachi", "KHI"), ("Lahore", "LHE"), ("Islamabad", "ISB")],
    ),
    "bangladesh": ("Bangladesh", [("Dhaka", "DAC"), ("Chittagong", "CGP")]),
    "iran": ("Iran", [("Tehran", "IKA"), ("Isfahan", "IFN"), ("Shiraz", "SYZ")]),
    "iraq": ("Iraq", [("Baghdad", "BGW"), ("Erbil", "EBL")]),
    "china": (
        "China",
        [
            ("Shanghai", "PVG"),
            ("Beijing", "PEK"),
            ("Chengdu", "CTU"),
            ("Guangzhou", "CAN"),
        ],
    ),
    "hong kong": ("Hong Kong", [("Hong Kong", "HKG")]),
    # ----- Middle East -----
    "uae": (
        "United Arab Emirates",
        [("Dubai", "DXB"), ("Abu Dhabi", "AUH"), ("Sharjah", "SHJ")],
    ),
    "united arab emirates": (
        "United Arab Emirates",
        [("Dubai", "DXB"), ("Abu Dhabi", "AUH")],
    ),
    "qatar": ("Qatar", [("Doha", "DOH")]),
    "bahrain": ("Bahrain", [("Manama", "BAH")]),
    "oman": ("Oman", [("Muscat", "MCT"), ("Salalah", "SLL")]),
    "jordan": ("Jordan", [("Amman", "AMM"), ("Aqaba", "AQJ")]),
    "lebanon": ("Lebanon", [("Beirut", "BEY")]),
    "israel": ("Israel", [("Tel Aviv", "TLV"), ("Eilat", "ETH")]),
    "turkey": (
        "Turkey",
        [("Istanbul", "IST"), ("Ankara", "ESB"), ("Antalya", "AYT"), ("Izmir", "ADB")],
    ),
    "saudi arabia": (
        "Saudi Arabia",
        [("Riyadh", "RUH"), ("Jeddah", "JED"), ("AlUla", "ULH")],
    ),
    # ----- Africa -----
    "morocco": (
        "Morocco",
        [
            ("Marrakech", "RAK"),
            ("Casablanca", "CMN"),
            ("Fes", "FEZ"),
            ("Agadir", "AGA"),
        ],
    ),
    "egypt": (
        "Egypt",
        [
            ("Cairo", "CAI"),
            ("Luxor", "LXR"),
            ("Sharm el-Sheikh", "SSH"),
            ("Hurghada", "HRG"),
        ],
    ),
    "kenya": ("Kenya", [("Nairobi", "NBO"), ("Mombasa", "MBA")]),
    "tanzania": (
        "Tanzania",
        [("Kilimanjaro", "JRO"), ("Dar es Salaam", "DAR"), ("Zanzibar", "ZNZ")],
    ),
    "south africa": (
        "South Africa",
        [("Cape Town", "CPT"), ("Johannesburg", "JNB"), ("Durban", "DUR")],
    ),
    "ethiopia": ("Ethiopia", [("Addis Ababa", "ADD")]),
    "namibia": ("Namibia", [("Windhoek", "WDH")]),
    "tunisia": ("Tunisia", [("Tunis", "TUN"), ("Djerba", "DJE"), ("Monastir", "MIR")]),
    "rwanda": ("Rwanda", [("Kigali", "KGL")]),
    "uganda": ("Uganda", [("Entebbe", "EBB")]),
    "nigeria": ("Nigeria", [("Lagos", "LOS"), ("Abuja", "ABV")]),
    "ghana": ("Ghana", [("Accra", "ACC")]),
    "senegal": ("Senegal", [("Dakar", "DSS")]),
    "ivory coast": ("Côte d'Ivoire", [("Abidjan", "ABJ")]),
    "cote d'ivoire": ("Côte d'Ivoire", [("Abidjan", "ABJ")]),
    "zimbabwe": ("Zimbabwe", [("Harare", "HRE"), ("Victoria Falls", "VFA")]),
    "zambia": ("Zambia", [("Lusaka", "LUN"), ("Livingstone", "LVI")]),
    "mozambique": ("Mozambique", [("Maputo", "MPM")]),
    "madagascar": ("Madagascar", [("Antananarivo", "TNR")]),
    "botswana": ("Botswana", [("Gaborone", "GBE"), ("Maun", "MUB")]),
    "algeria": ("Algeria", [("Algiers", "ALG"), ("Oran", "ORN")]),
    "libya": ("Libya", [("Tripoli", "TIP"), ("Benghazi", "BEN")]),
    "sudan": ("Sudan", [("Khartoum", "KRT")]),
    # ----- Oceania -----
    "australia": (
        "Australia",
        [
            ("Sydney", "SYD"),
            ("Melbourne", "MEL"),
            ("Brisbane", "BNE"),
            ("Cairns", "CNS"),
            ("Perth", "PER"),
        ],
    ),
    "new zealand": (
        "New Zealand",
        [("Auckland", "AKL"), ("Queenstown", "ZQN"), ("Christchurch", "CHC")],
    ),
    "fiji": ("Fiji", [("Nadi", "NAN")]),
    # ----- Americas -----
    "usa": (
        "United States",
        [
            ("New York", "JFK"),
            ("Los Angeles", "LAX"),
            ("Miami", "MIA"),
            ("Chicago", "ORD"),
            ("Las Vegas", "LAS"),
        ],
    ),
    "united states": (
        "United States",
        [
            ("New York", "JFK"),
            ("Los Angeles", "LAX"),
            ("Miami", "MIA"),
            ("Chicago", "ORD"),
        ],
    ),
    "us": (
        "United States",
        [("New York", "JFK"), ("Los Angeles", "LAX"), ("Miami", "MIA")],
    ),
    "america": (
        "United States",
        [("New York", "JFK"), ("Los Angeles", "LAX"), ("Miami", "MIA")],
    ),
    "canada": (
        "Canada",
        [
            ("Toronto", "YYZ"),
            ("Vancouver", "YVR"),
            ("Montreal", "YUL"),
            ("Calgary", "YYC"),
        ],
    ),
    "mexico": (
        "Mexico",
        [
            ("Cancún", "CUN"),
            ("Mexico City", "MEX"),
            ("Los Cabos", "SJD"),
            ("Puerto Vallarta", "PVR"),
        ],
    ),
    "brazil": (
        "Brazil",
        [
            ("Rio de Janeiro", "GIG"),
            ("São Paulo", "GRU"),
            ("Salvador", "SSA"),
            ("Florianópolis", "FLN"),
        ],
    ),
    "argentina": (
        "Argentina",
        [("Buenos Aires", "EZE"), ("Mendoza", "MDZ"), ("Bariloche", "BRC")],
    ),
    "peru": ("Peru", [("Cusco", "CUZ"), ("Lima", "LIM"), ("Arequipa", "AQP")]),
    "chile": ("Chile", [("Santiago", "SCL"), ("Punta Arenas", "PUQ")]),
    "colombia": (
        "Colombia",
        [("Cartagena", "CTG"), ("Bogotá", "BOG"), ("Medellín", "MDE")],
    ),
    "ecuador": (
        "Ecuador",
        [("Quito", "UIO"), ("Guayaquil", "GYE"), ("Galapagos", "GPS")],
    ),
    "bolivia": ("Bolivia", [("La Paz", "LPB"), ("Sucre", "SRE")]),
    "cuba": ("Cuba", [("Havana", "HAV"), ("Varadero", "VRA"), ("Holguín", "HOG")]),
    "jamaica": ("Jamaica", [("Montego Bay", "MBJ"), ("Kingston", "KIN")]),
    "panama": ("Panama", [("Panama City", "PTY")]),
    "costa rica": ("Costa Rica", [("San José", "SJO"), ("Liberia", "LIR")]),
    "dominican republic": (
        "Dominican Republic",
        [("Punta Cana", "PUJ"), ("Santo Domingo", "SDQ"), ("Puerto Plata", "POP")],
    ),
    "guatemala": ("Guatemala", [("Guatemala City", "GUA")]),
    "uruguay": ("Uruguay", [("Montevideo", "MVD"), ("Punta del Este", "PDP")]),
    "venezuela": ("Venezuela", [("Caracas", "CCS"), ("Margarita Island", "PMV")]),
    "paraguay": ("Paraguay", [("Asunción", "ASU")]),
    "haiti": ("Haiti", [("Port-au-Prince", "PAP")]),
    "trinidad and tobago": ("Trinidad and Tobago", [("Port of Spain", "POS")]),
    "honduras": ("Honduras", [("Tegucigalpa", "TGU"), ("Roatán", "RTB")]),
    "el salvador": ("El Salvador", [("San Salvador", "SAL")]),
    "nicaragua": ("Nicaragua", [("Managua", "MGA")]),
}


def _normalise(country: str) -> str:
    """Lowercase + strip leading article so 'the UK' and 'UK' hash the same."""
    s = country.strip().lower()
    if s.startswith("the "):
        s = s[4:]
    return s


def lookup_country_tourist_hubs(
    country: str,
) -> tuple[str, list[tuple[str, str]]] | None:
    """Return ``(display_name, [(city, iata), ...])`` for a known country.

    Hubs are in priority order — first entry is the primary hub used for
    backward-compat single-hub callers and as the booking session anchor.

    ``None`` when the country isn't in the static table.

    >>> lookup_country_tourist_hubs("Montenegro")
    ('Montenegro', [('Kotor', 'TIV'), ('Podgorica', 'TGD')])
    >>> lookup_country_tourist_hubs("the UK")
    ('United Kingdom', [('London', 'LHR'), ('Edinburgh', 'EDI'), ('Manchester', 'MAN')])
    >>> lookup_country_tourist_hubs("Mars") is None
    True
    """
    if not country or not country.strip():
        return None
    return _COUNTRY_TOURIST_HUBS.get(_normalise(country))


def lookup_country_tourist_hub(country: str) -> tuple[str, str, str] | None:
    """Return ``(city, iata, country_display_name)`` for the PRIMARY hub.

    Backward-compatible wrapper over :func:`lookup_country_tourist_hubs`.
    Returns only the first (highest-priority) hub so existing callers that
    expect a single hub are unaffected.

    >>> lookup_country_tourist_hub("Montenegro")
    ('Kotor', 'TIV', 'Montenegro')
    >>> lookup_country_tourist_hub("the UK")
    ('London', 'LHR', 'United Kingdom')
    >>> lookup_country_tourist_hub("Mars") is None
    True
    """
    result = lookup_country_tourist_hubs(country)
    if result is None:
        return None
    display_name, hubs = result
    if not hubs:
        return None
    city, iata = hubs[0]
    return city, iata, display_name


__all__ = ["lookup_country_tourist_hub", "lookup_country_tourist_hubs"]
