import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="indonesia-geocoder")

INDONESIA_PROVINCES = {
    "aceh",
    "sumatera utara",
    "sumatera barat",
    "riau",
    "kepulauan riau",
    "jambi",
    "sumatera selatan",
    "kepulauan bangka belitung",
    "bengkulu",
    "lampung",
    "dki jakarta",
    "jakarta",
    "jawa barat",
    "jawa tengah",
    "di yogyakarta",
    "yogyakarta",
    "jawa timur",
    "banten",
    "bali",
    "nusa tenggara barat",
    "nusa tenggara timur",
    "kalimantan barat",
    "kalimantan tengah",
    "kalimantan selatan",
    "kalimantan timur",
    "kalimantan utara",
    "sulawesi utara",
    "sulawesi tengah",
    "sulawesi selatan",
    "sulawesi tenggara",
    "gorontalo",
    "sulawesi barat",
    "maluku",
    "maluku utara",
    "papua",
    "papua barat",
    "papua selatan",
    "papua tengah",
    "papua pegunungan",
    "papua barat daya",
}

INDONESIA_CITIES = {
    "jakarta",
    "bogor",
    "depok",
    "tangerang",
    "tangerang selatan",
    "bekasi",
    "bandung",
    "surabaya",
    "semarang",
    "medan",
    "palembang",
    "padang",
    "pekanbaru",
    "batam",
    "denpasar",
    "makassar",
    "manado",
    "ambon",
    "jayapura",
    "pontianak",
    "banjarmasin",
    "samarinda",
    "balikpapan",
    "malang",
    "solo",
    "yogyakarta",
}

INDONESIA_PROVINCES_EN = {
    "aceh",
    "north sumatra",
    "west sumatra",
    "riau",
    "riau islands",
    "jambi",
    "south sumatra",
    "bangka belitung islands",
    "bengkulu",
    "lampung",
    "special capital region of jakarta",
    "jakarta",
    "west java",
    "central java",
    "special region of yogyakarta",
    "yogyakarta",
    "east java",
    "banten",
    "bali",
    "west nusa tenggara",
    "east nusa tenggara",
    "west kalimantan",
    "central kalimantan",
    "south kalimantan",
    "east kalimantan",
    "north kalimantan",
    "north sulawesi",
    "central sulawesi",
    "south sulawesi",
    "southeast sulawesi",
    "gorontalo",
    "west sulawesi",
    "maluku",
    "north maluku",
    "papua",
    "west papua",
    "south papua",
    "central papua",
    "highland papua",
    "southwest papua",
}

INDONESIA_CITIES_EN = {
    "jakarta",
    "bogor",
    "depok",
    "tangerang",
    "south tangerang",
    "bekasi",
    "bandung",
    "surabaya",
    "semarang",
    "medan",
    "palembang",
    "padang",
    "pekanbaru",
    "batam",
    "denpasar",
    "makassar",
    "manado",
    "ambon",
    "jayapura",
    "pontianak",
    "banjarmasin",
    "samarinda",
    "balikpapan",
    "malang",
    "surakarta",
    "yogyakarta",
}

def extract_indonesia_location(user_input: str) -> str | None:
    if not user_input:
        return None

    text = re.sub(r"[^\w\s]", " ", user_input.lower())
    locations = INDONESIA_PROVINCES | INDONESIA_CITIES | INDONESIA_CITIES_EN | INDONESIA_PROVINCES_EN

    for location in locations:
        if re.search(rf"\b{re.escape(location)}\b", text):
            return location

    return None


def get_geolocation_indonesia(place_name: str):
    """
    Returns (latitude, longitude, display_name) or None
    """
    try:
        location = geolocator.geocode(
            f"{place_name}, Indonesia",
            exactly_one=True,
            addressdetails=True,
            timeout=10
        )
        if location:
            print(f"latitude: {location.latitude}, longitude: {location.longitude}")
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        pass

    return None