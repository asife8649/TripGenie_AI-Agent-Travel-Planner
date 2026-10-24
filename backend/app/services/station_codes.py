# Major railway stations used when the optional Indian Railways API is configured.
# city (lowercase) -> (station_code, station_name)
# Cities with several stations map to the main long-distance station. If a city is
# missing, rail_api.py asks the provider's station-search endpoint instead.

STATION_CODES = {
    "kolkata": ("HWH", "Howrah Jn"),
    "howrah": ("HWH", "Howrah Jn"),
    "sealdah": ("SDAH", "Sealdah"),
    "delhi": ("NDLS", "New Delhi"),
    "new delhi": ("NDLS", "New Delhi"),
    "mumbai": ("CSMT", "Mumbai CSMT"),
    "chennai": ("MAS", "Chennai Central"),
    "bangalore": ("SBC", "KSR Bengaluru"),
    "bengaluru": ("SBC", "KSR Bengaluru"),
    "hyderabad": ("SC", "Secunderabad Jn"),
    "pune": ("PUNE", "Pune Jn"),
    "ahmedabad": ("ADI", "Ahmedabad Jn"),
    "siliguri": ("NJP", "New Jalpaiguri"),
    "darjeeling": ("NJP", "New Jalpaiguri"),
    "guwahati": ("GHY", "Guwahati"),
    "patna": ("PNBE", "Patna Jn"),
    "varanasi": ("BSB", "Varanasi Jn"),
    "lucknow": ("LKO", "Lucknow NR"),
    "jaipur": ("JP", "Jaipur Jn"),
    "bhubaneswar": ("BBS", "Bhubaneswar"),
    "puri": ("PURI", "Puri"),
    "thiruvananthapuram": ("TVC", "Thiruvananthapuram Central"),
    "trivandrum": ("TVC", "Thiruvananthapuram Central"),
    "kochi": ("ERS", "Ernakulam Jn"),
    "ernakulam": ("ERS", "Ernakulam Jn"),
    "amritsar": ("ASR", "Amritsar Jn"),
    "chandigarh": ("CDG", "Chandigarh"),
    "dehradun": ("DDN", "Dehradun"),
    "haridwar": ("HW", "Haridwar Jn"),
    "bhopal": ("BPL", "Bhopal Jn"),
    "nagpur": ("NGP", "Nagpur"),
    "ranchi": ("RNC", "Ranchi Jn"),
    "gaya": ("GAYA", "Gaya Jn"),
    "agra": ("AGC", "Agra Cantt"),
    "jodhpur": ("JU", "Jodhpur Jn"),
    "udaipur": ("UDZ", "Udaipur City"),
    "goa": ("MAO", "Madgaon Jn"),
    "madgaon": ("MAO", "Madgaon Jn"),
    "visakhapatnam": ("VSKP", "Visakhapatnam Jn"),
    "vizag": ("VSKP", "Visakhapatnam Jn"),
    "murshidabad": ("MBB", "Murshidabad"),
    "lalgola": ("LGL", "Lalgola"),
    "durgapur": ("DGR", "Durgapur"),
    "asansol": ("ASN", "Asansol Jn"),
    "bardhaman": ("BWN", "Barddhaman Jn"),
    "shantiniketan": ("BHP", "Bolpur Shantiniketan"),
    "bolpur": ("BHP", "Bolpur Shantiniketan"),
}


def get_station(city: str):
    return STATION_CODES.get(" ".join(str(city or "").lower().split()))
