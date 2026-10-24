# Common Indian airport codes (city -> IATA).
# Places without a commercial airport map to the nearest usable airport and
# are listed in AIRPORT_NOTES so the UI can tell the traveller.

AIRPORT_CODES = {
    "kolkata": "CCU", "calcutta": "CCU",
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "chennai": "MAA", "hyderabad": "HYD", "pune": "PNQ", "ahmedabad": "AMD",
    "goa": "GOI", "dabolim": "GOI",
    "bagdogra": "IXB", "siliguri": "IXB", "darjeeling": "IXB",
    "guwahati": "GAU", "jaipur": "JAI", "lucknow": "LKO", "patna": "PAT",
    "bhubaneswar": "BBI", "ranchi": "IXR", "varanasi": "VNS", "amritsar": "ATQ",
    "kochi": "COK", "cochin": "COK", "thiruvananthapuram": "TRV", "trivandrum": "TRV",
    "coimbatore": "CJB", "madurai": "IXM", "tiruchirappalli": "TRZ", "trichy": "TRZ",
    "mangalore": "IXE", "mangaluru": "IXE", "visakhapatnam": "VTZ", "vizag": "VTZ",
    "nagpur": "NAG", "indore": "IDR", "bhopal": "BHO", "raipur": "RPR",
    "chandigarh": "IXC", "dehradun": "DED", "udaipur": "UDR", "jodhpur": "JDH",
    "srinagar": "SXR", "leh": "IXL", "jammu": "IXJ", "agartala": "IXA",
    "imphal": "IMF", "port blair": "IXZ", "gaya": "GAY", "surat": "STV",
    "vadodara": "BDQ", "rajkot": "RAJ", "tirupati": "TIR", "pondicherry": "PNY",
    "shillong": "SHL", "dibrugarh": "DIB", "jorhat": "JRH", "silchar": "IXS",
    "durgapur": "RDP", "andal": "RDP",
    # No airport of their own -> nearest practical airport
    "murshidabad": "CCU", "berhampore": "CCU", "digha": "CCU", "shantiniketan": "CCU",
    "sundarbans": "CCU", "puri": "BBI", "konark": "BBI", "gangtok": "IXB",
    "kalimpong": "IXB", "mussoorie": "DED", "rishikesh": "DED", "haridwar": "DED",
    "manali": "KUU", "shimla": "SLV", "munnar": "COK", "alleppey": "COK",
    "alappuzha": "COK", "ooty": "CJB", "kodaikanal": "IXM", "hampi": "VDY",
}

AIRPORT_NOTES = {
    "murshidabad": "Murshidabad has no airport. Nearest: Kolkata (CCU), roughly 4–5 hr by road/train.",
    "berhampore": "Berhampore has no airport. Nearest: Kolkata (CCU).",
    "digha": "Digha has no airport. Nearest: Kolkata (CCU), roughly 5 hr by road.",
    "shantiniketan": "Shantiniketan has no airport. Nearest: Kolkata (CCU).",
    "sundarbans": "Sundarbans has no airport. Nearest: Kolkata (CCU).",
    "puri": "Puri has no airport. Nearest: Bhubaneswar (BBI), about 1.5 hr by road.",
    "konark": "Konark has no airport. Nearest: Bhubaneswar (BBI).",
    "gangtok": "Gangtok has no airport. Nearest: Bagdogra (IXB), about 4–5 hr by road.",
    "darjeeling": "Darjeeling has no airport. Nearest: Bagdogra (IXB), about 3 hr by road.",
    "kalimpong": "Kalimpong has no airport. Nearest: Bagdogra (IXB).",
    "siliguri": "Siliguri is served by Bagdogra airport (IXB).",
    "mussoorie": "Mussoorie has no airport. Nearest: Dehradun (DED).",
    "rishikesh": "Rishikesh has no airport. Nearest: Dehradun (DED).",
    "haridwar": "Haridwar has no airport. Nearest: Dehradun (DED).",
    "manali": "Manali has no major airport. Nearest: Kullu–Manali (KUU).",
    "shimla": "Shimla airport has very limited service.",
    "munnar": "Munnar has no airport. Nearest: Kochi (COK), about 4 hr by road.",
    "alleppey": "Alleppey has no airport. Nearest: Kochi (COK).",
    "alappuzha": "Alappuzha has no airport. Nearest: Kochi (COK).",
    "ooty": "Ooty has no airport. Nearest: Coimbatore (CJB).",
    "kodaikanal": "Kodaikanal has no airport. Nearest: Madurai (IXM).",
    "hampi": "Hampi has no airport. Nearest: Vidyanagar/Hubballi region.",
}


def get_airport_code(city: str):
    return AIRPORT_CODES.get(str(city or "").strip().lower())


def get_airport_note(city: str):
    return AIRPORT_NOTES.get(str(city or "").strip().lower())
