import re
from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="indonesia-geocoder")

# Offline coordinate database for Indonesian regencies/cities, focused on volcanic regions & major centers.
PREDEFINED_INDONESIA_COORDINATES: dict[str, tuple[float, float]] = {
    # DI Yogyakarta & Jateng (Merapi, Slamet, Sindoro, Sumbing, Dieng)
    "sleman": (-7.7167, 110.3556),
    "magelang": (-7.4706, 110.2178),
    "boyolali": (-7.5361, 110.5944),
    "klaten": (-7.7056, 110.6044),
    "yogyakarta": (-7.7956, 110.3695),
    "di yogyakarta": (-7.7956, 110.3695),
    "jogja": (-7.7956, 110.3695),
    "jogjakarta": (-7.7956, 110.3695),
    "bantul": (-7.8878, 110.3283),
    "kulon progo": (-7.8283, 110.1581),
    "kulonprogo": (-7.8283, 110.1581),
    "gunungkidul": (-7.9606, 110.6014),
    "gunung kidul": (-7.9606, 110.6014),
    "semarang": (-6.9667, 110.4167),
    "surakarta": (-7.5667, 110.8167),
    "solo": (-7.5667, 110.8167),
    "salatiga": (-7.3306, 110.5083),
    "sukoharjo": (-7.6833, 110.8333),
    "karanganyar": (-7.5967, 110.9458),
    "sragen": (-7.4278, 111.0219),
    "wonogiri": (-7.8139, 110.9256),
    "wonosobo": (-7.3631, 109.9000),
    "temanggung": (-7.3167, 110.1667),
    "banjarnegara": (-7.3986, 109.6978),
    "purbalingga": (-7.3889, 109.3639),
    "banyumas": (-7.4314, 109.2464),
    "purwokerto": (-7.4314, 109.2464),
    "cilacap": (-7.7183, 109.0158),
    "kebumen": (-7.6686, 109.6514),
    "purworejo": (-7.7144, 110.0078),
    "pekalongan": (-6.8886, 109.6753),
    "batang": (-6.9114, 109.7303),
    "pemalang": (-6.8906, 109.3808),
    "tegal": (-6.8694, 109.1403),
    "brebes": (-6.8706, 109.0417),
    "kudus": (-6.8047, 110.8406),
    "pati": (-6.7561, 111.0378),
    "jepara": (-6.5928, 110.6778),
    "rembang": (-6.7106, 111.3414),
    "blora": (-6.9697, 111.4186),
    "grobogan": (-7.0869, 110.9167),
    "purwodadi": (-7.0869, 110.9167),
    "demak": (-6.8944, 110.6389),
    "kendal": (-6.9247, 110.2039),

    # Jawa Barat & Banten (Gede, Pangrango, Tangkuban Parahu, Papandayan, Guntur, Galunggung, Salak, Ciremai, Anak Krakatau)
    "badan geologi": (-6.9008, 107.6214),
    "museum geologi": (-6.9008, 107.6214),
    "kantor badan geologi": (-6.9008, 107.6214),
    "pvmbg": (-6.9008, 107.6214),
    "diponegoro bandung": (-6.9008, 107.6214),
    "jalan diponegoro bandung": (-6.9008, 107.6214),
    "jl diponegoro bandung": (-6.9008, 107.6214),
    "gedung sate": (-6.9025, 107.6186),
    "taman lansia": (-6.9015, 107.6225),
    "naripan": (-6.9202, 107.6084),
    "braga": (-6.9175, 107.6095),
    "alun alun bandung": (-6.9219, 107.6071),
    "bandung": (-6.9175, 107.6191),
    "bandung barat": (-6.8436, 107.5028),
    "cimahi": (-6.8722, 107.5422),
    "bogor": (-6.5971, 106.8060),
    "sukabumi": (-6.9277, 106.9300),
    "cianjur": (-6.8173, 107.1378),
    "garut": (-7.2278, 107.9086),
    "tasikmalaya": (-7.3274, 108.2207),
    "ciamis": (-7.3256, 108.3533),
    "banjar": (-7.3742, 108.5342),
    "pangandaran": (-7.6833, 108.6500),
    "sumedang": (-6.8586, 107.9267),
    "kuningan": (-6.9767, 108.4833),
    "cirebon": (-6.7320, 108.5523),
    "majalengka": (-6.8361, 108.2278),
    "subang": (-6.5694, 107.7583),
    "purwakarta": (-6.5569, 107.4433),
    "karawang": (-6.3073, 107.3019),
    "bekasi": (-6.2383, 106.9756),
    "depok": (-6.4025, 106.7942),
    "jakarta": (-6.2088, 106.8456),
    "dki jakarta": (-6.2088, 106.8456),
    "tangerang": (-6.1783, 106.6319),
    "tangerang selatan": (-6.2889, 106.7178),
    "serang": (-6.1104, 106.1640),
    "cilegon": (-6.0178, 106.0539),
    "lebak": (-6.5386, 106.2483),
    "pandeglang": (-6.3083, 106.1067),

    # Jawa Timur (Semeru, Bromo, Kelud, Raung, Ijen, Arjuno-Welirang, Lamongan)
    "surabaya": (-7.2575, 112.7521),
    "malang": (-7.9797, 112.6304),
    "batu": (-7.8700, 112.5272),
    "lumajang": (-8.1333, 113.2167),
    "probolinggo": (-7.7544, 113.2158),
    "pasuruan": (-7.6453, 112.9075),
    "banyuwangi": (-8.2192, 114.3692),
    "jember": (-8.1724, 113.7008),
    "bondowoso": (-7.9133, 113.8214),
    "situbondo": (-7.7064, 114.0044),
    "kediri": (-7.8167, 112.0167),
    "blitar": (-8.0983, 112.1681),
    "tulungagung": (-8.0667, 111.9000),
    "trenggalek": (-8.0500, 111.7167),
    "ponorogo": (-7.8686, 111.4622),
    "pacitan": (-8.2064, 111.0928),
    "madiun": (-7.6298, 111.5239),
    "magetan": (-7.6539, 111.3281),
    "ngawi": (-7.4039, 111.4447),
    "bojonegoro": (-7.1500, 111.8833),
    "tuban": (-6.8978, 112.0647),
    "lamongan": (-7.1197, 112.4131),
    "gresik": (-7.1564, 112.6558),
    "sidoarjo": (-7.4478, 112.7183),
    "mojokerto": (-7.4725, 112.4381),
    "jombang": (-7.5461, 112.2331),
    "nganjuk": (-7.6047, 111.9042),

    # Bali & Nusa Tenggara (Agung, Batur, Rinjani, Tambora, Sangeang Api, Lewotobi, Lewotolo, Inielika, Kelimutu, Egon, Iya, Sirung)
    "denpasar": (-8.6705, 115.2126),
    "badung": (-8.5833, 115.1833),
    "gianyar": (-8.5442, 115.3267),
    "tabanan": (-8.5392, 115.1247),
    "klungkung": (-8.5358, 115.4039),
    "bangli": (-8.4542, 115.3550),
    "karangasem": (-8.4489, 115.6139),
    "buleleng": (-8.1122, 115.0881),
    "singaraja": (-8.1122, 115.0881),
    "jembrana": (-8.3586, 114.6289),
    "mataram": (-8.5833, 116.1167),
    "lombok barat": (-8.6833, 116.1333),
    "lombok tengah": (-8.7000, 116.2667),
    "lombok timur": (-8.6500, 116.5333),
    "lombok utara": (-8.3500, 116.1667),
    "sumbawa": (-8.5000, 117.4167),
    "sumbawa barat": (-8.7478, 116.8458),
    "dompu": (-8.5333, 118.4500),
    "bima": (-8.4608, 118.7269),
    "kupang": (-10.1772, 123.6070),
    "manggarai barat": (-8.4964, 119.8877),
    "labuan bajo": (-8.4964, 119.8877),
    "manggarai": (-8.6139, 120.4639),
    "ruteng": (-8.6139, 120.4639),
    "manggarai timur": (-8.6000, 120.6500),
    "ngada": (-8.7917, 120.9639),
    "bajawa": (-8.7917, 120.9639),
    "nagekeo": (-8.6742, 121.2858),
    "mbay": (-8.6742, 121.2858),
    "ende": (-8.8433, 121.6622),
    "sikka": (-8.6197, 122.2106),
    "maumere": (-8.6197, 122.2106),
    "flores timur": (-8.3431, 122.9817),
    "larantuka": (-8.3431, 122.9817),
    "lembata": (-8.3667, 123.5500),
    "lewoleba": (-8.3667, 123.5500),
    "alor": (-8.2189, 124.5183),
    "kalabahi": (-8.2189, 124.5183),
    "sumba timur": (-9.6542, 120.2642),
    "waingapu": (-9.6542, 120.2642),
    "sumba barat": (-9.6367, 119.3139),

    # Sumatera (Sinabung, Sibayak, Marapi, Singgalang, Tandikat, Kerinci, Talang, Dempo, Kaba, Sorikmarapi, Seulawah Agam)
    "medan": (3.5952, 98.6722),
    "karo": (3.1783, 98.4908),
    "kabanjahe": (3.1783, 98.4908),
    "berastagi": (3.1833, 98.5167),
    "simalungun": (2.9583, 99.0667),
    "dairi": (2.7500, 98.3167),
    "toba": (2.3333, 99.0667),
    "tapanuli utara": (2.0167, 98.9667),
    "tarutung": (2.0167, 98.9667),
    "tapanuli tengah": (1.7428, 98.7792),
    "sibolga": (1.7428, 98.7792),
    "mandailing natal": (0.8667, 99.5833),
    "padang": (-0.9471, 100.4172),
    "bukittinggi": (-0.3056, 100.3692),
    "padang panjang": (-0.4639, 100.3986),
    "payakumbuh": (-0.2289, 100.6319),
    "agam": (-0.3000, 100.0333),
    "tanah datar": (-0.4500, 100.5833),
    "batusangkar": (-0.4500, 100.5833),
    "solok": (-0.7986, 100.6583),
    "solok selatan": (-1.5167, 101.2167),
    "pasaman": (0.1333, 100.1667),
    "kerinci": (-2.0589, 101.3917),
    "sungai penuh": (-2.0589, 101.3917),
    "jambi": (-1.6101, 103.6131),
    "palembang": (-2.9909, 104.7565),
    "pagar alam": (-4.0167, 103.2667),
    "pagaralam": (-4.0167, 103.2667),
    "lahat": (-3.7833, 103.5333),
    "muara enim": (-3.6500, 103.7667),
    "bengkulu": (-3.8004, 102.2655),
    "rejang lebong": (-3.4667, 102.5333),
    "curup": (-3.4667, 102.5333),
    "kepahiang": (-3.6333, 102.5833),
    "bandar lampung": (-5.4500, 105.2667),
    "lampung selatan": (-5.7333, 105.5833),
    "kalianda": (-5.7333, 105.5833),
    "lampung barat": (-5.0333, 104.0667),
    "tanggamus": (-5.5000, 104.6167),
    "banda aceh": (5.5483, 95.3238),
    "sabang": (5.8933, 95.3214),
    "aceh besar": (5.2833, 95.6167),
    "bener meriah": (4.7208, 96.8625),
    "aceh tengah": (4.6289, 96.8458),
    "takengon": (4.6289, 96.8458),

    # Sulawesi & Maluku (Lokon, Soputan, Karangetang, Ruang, Awu, Gamalama, Dukono, Ibu, Gamkonora)
    "manado": (1.4748, 124.8428),
    "tomohon": (1.3283, 124.8406),
    "bitung": (1.4404, 125.1217),
    "minahasa": (1.3114, 124.9125),
    "minahasa utara": (1.4058, 124.9814),
    "minahasa selatan": (1.1833, 124.5833),
    "minahasa tenggara": (1.0333, 124.7833),
    "kotamobagu": (0.7306, 124.3139),
    "sitaro": (2.7333, 125.3833),
    "kepulauan sitaro": (2.7333, 125.3833),
    "sangihe": (3.6111, 125.4889),
    "kepulauan sangihe": (3.6111, 125.4889),
    "talaud": (4.0000, 126.7000),
    "ternate": (0.7893, 127.3639),
    "tidore": (0.6917, 127.4333),
    "halmahera barat": (1.0667, 127.4833),
    "jailolo": (1.0667, 127.4833),
    "halmahera utara": (1.7278, 128.0083),
    "tobelo": (1.7278, 128.0083),
    "halmahera selatan": (-0.6333, 127.4833),
    "halmahera tengah": (0.4500, 127.8833),
    "halmahera timur": (1.2000, 128.3000),
    "morotai": (2.0500, 128.3000),
    "ambon": (-3.6958, 128.1814),
    "banda neira": (-4.5247, 129.9042),
    "banda": (-4.5247, 129.9042),
    "maluku tengah": (-3.3000, 128.9500),
    "masohi": (-3.3000, 128.9500),
    "seram bagian barat": (-3.1000, 128.2500),
    "seram bagian timur": (-3.1500, 130.5000),
    "makassar": (-5.1477, 119.4327),
    "gowa": (-5.2000, 119.4500),
    "maros": (-5.0000, 119.5667),
    "palu": (-0.8917, 119.8707),
    "poso": (-1.3833, 120.7500),
    "gorontalo": (0.5435, 123.0568),
    "kendari": (-3.9985, 122.5126),
    "mamuju": (-2.6748, 118.8855),

    # Kalimantan & Papua
    "pontianak": (-0.0263, 109.3425),
    "banjarmasin": (-3.3194, 114.5908),
    "samarinda": (-0.5022, 117.1536),
    "balikpapan": (-1.2379, 116.8289),
    "palangka raya": (-2.2078, 113.9164),
    "jayapura": (-2.5337, 140.7181),
    "merauke": (-8.4991, 140.4014),
    "timika": (-4.5444, 136.8833),
    "manokwari": (-0.8615, 134.0620),
    "sorong": (-0.8762, 131.2558),
}

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

INDONESIA_CITIES = set(PREDEFINED_INDONESIA_COORDINATES.keys())

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
    "solo",
    "yogyakarta",
    "sleman",
    "magelang",
    "boyolali",
    "klaten",
    "garut",
    "sukabumi",
}

# Longest names first so compound place names are matched accurately (e.g. "bandung barat" before "bandung")
_ALL_LOCATIONS = sorted(
    INDONESIA_PROVINCES
    | INDONESIA_CITIES
    | INDONESIA_CITIES_EN
    | INDONESIA_PROVINCES_EN
    | set(PREDEFINED_INDONESIA_COORDINATES.keys()),
    key=len,
    reverse=True,
)


def extract_indonesia_location(user_input: str) -> Optional[str]:
    if not user_input:
        return None

    text = re.sub(r"[^\w\s]", " ", user_input.lower())

    for location in _ALL_LOCATIONS:
        if re.search(rf"\b{re.escape(location)}\b", text):
            return location

    return None


_GEOCODE_CACHE: dict[str, tuple[float, float]] = {}


def get_geolocation_indonesia(place_name: str) -> Optional[Tuple[float, float]]:
    """
    Returns (latitude, longitude) or None.
    Prioritizes instant offline coordinates dictionary for high accuracy and 0ms latency.
    Falls back to Nominatim and caches the result.
    """
    if not place_name:
        return None
    key = place_name.strip().lower()

    # 1. Offline high-precision dictionary
    if key in PREDEFINED_INDONESIA_COORDINATES:
        return PREDEFINED_INDONESIA_COORDINATES[key]

    # Check without prefix like "kota", "kabupaten", "kab"
    cleaned_key = re.sub(r"\b(kota|kabupaten|kab|daerah|provinsi|propinsi)\b", "", key).strip()
    if cleaned_key in PREDEFINED_INDONESIA_COORDINATES:
        return PREDEFINED_INDONESIA_COORDINATES[cleaned_key]

    # 2. In-memory cache
    if key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[key]

    # 3. Nominatim geocoder fallback
    try:
        location = geolocator.geocode(
            f"{place_name}, Indonesia",
            exactly_one=True,
            addressdetails=True,
            country_codes="id",
            timeout=10,
        )
        if location:
            print(f"[GEOCODER] Nominatim matched {place_name}: {location.latitude}, {location.longitude}")
            coords = (location.latitude, location.longitude)
            if len(_GEOCODE_CACHE) < 512:
                _GEOCODE_CACHE[key] = coords
            return coords
    except Exception as exc:
        print(f"[GEOCODER] Geocoding failed for {place_name!r}: {exc}")

    return None