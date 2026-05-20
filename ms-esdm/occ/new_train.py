import os
import random
import pandas as pd
import joblib
import numpy as np
import xgboost as xgb
import re
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from fastembed import TextEmbedding
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import OneClassSVM

# ======================================================
# Configuration
# ======================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Create output directory structure
OUTPUT_DIR = "magma_intent_model"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create subdirectories
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Training timestamp
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

volcano_data = [
    {"ga_nama_gapi": "Agung", "ga_code": "AGU"},
    {"ga_nama_gapi": "Ambang", "ga_code": "AMB"},
    {"ga_nama_gapi": "Anak Krakatau", "ga_code": "KRA"},
    {"ga_nama_gapi": "Anak Ranakah", "ga_code": "RAN"},
    {"ga_nama_gapi": "Arjuno Welirang", "ga_code": "WEL"},
    {"ga_nama_gapi": "Awu", "ga_code": "AWU"},
    {"ga_nama_gapi": "Banda Api", "ga_code": "BAN"},
    {"ga_nama_gapi": "Batur", "ga_code": "BAT"},
    {"ga_nama_gapi": "Batutara", "ga_code": "TAR"},
    {"ga_nama_gapi": "Bromo", "ga_code": "BRO"},
    {"ga_nama_gapi": "Bur Ni Telong", "ga_code": "TEL"},
    {"ga_nama_gapi": "Ciremai", "ga_code": "CER"},
    {"ga_nama_gapi": "Colo", "ga_code": "COL"},
    {"ga_nama_gapi": "Dempo", "ga_code": "DEM"},
    {"ga_nama_gapi": "Dieng", "ga_code": "DIE"},
    {"ga_nama_gapi": "Dukono", "ga_code": "DUK"},
    {"ga_nama_gapi": "Ebulobo", "ga_code": "EBU"},
    {"ga_nama_gapi": "Egon", "ga_code": "EGO"},
    {"ga_nama_gapi": "Galunggung", "ga_code": "GAL"},
    {"ga_nama_gapi": "Gamalama", "ga_code": "GML"},
    {"ga_nama_gapi": "Gamkonora", "ga_code": "GMK"},
    {"ga_nama_gapi": "Gede", "ga_code": "GED"},
    {"ga_nama_gapi": "Guntur", "ga_code": "GUN"},
    {"ga_nama_gapi": "Hobal", "ga_code": "HOB"},
    {"ga_nama_gapi": "Ibu", "ga_code": "IBU"},
    {"ga_nama_gapi": "Ijen", "ga_code": "IJE"},
    {"ga_nama_gapi": "Ile Werung", "ga_code": "WER"},
    {"ga_nama_gapi": "Ili Boleng", "ga_code": "BOL"},
    {"ga_nama_gapi": "Ili Lewotolok", "ga_code": "LEW"},
    {"ga_nama_gapi": "Inielika", "ga_code": "LIK"},
    {"ga_nama_gapi": "Inierie", "ga_code": "RIE"},
    {"ga_nama_gapi": "Iya", "ga_code": "IYA"},
    {"ga_nama_gapi": "Kaba", "ga_code": "KAB"},
    {"ga_nama_gapi": "Karangetang", "ga_code": "KAR"},
    {"ga_nama_gapi": "Kelimutu", "ga_code": "KLM"},
    {"ga_nama_gapi": "Kelud", "ga_code": "KLD"},
    {"ga_nama_gapi": "Kerinci", "ga_code": "KER"},
    {"ga_nama_gapi": "Kie Besi", "ga_code": "KIE"},
    {"ga_nama_gapi": "Lamongan", "ga_code": "LAM"},
    {"ga_nama_gapi": "Lereboleng", "ga_code": "LER"},
    {"ga_nama_gapi": "Lewotobi Laki-laki", "ga_code": "LWK"},
    {"ga_nama_gapi": "Lewotobi Perempuan", "ga_code": "LWP"},
    {"ga_nama_gapi": "Lokon", "ga_code": "LOK"},
    {"ga_nama_gapi": "Mahawu", "ga_code": "MAH"},
    {"ga_nama_gapi": "Marapi", "ga_code": "MAR"},
    {"ga_nama_gapi": "Merapi", "ga_code": "MER"},
    {"ga_nama_gapi": "Papandayan", "ga_code": "PAP"},
    {"ga_nama_gapi": "Peut Sague", "ga_code": "PEU"},
    {"ga_nama_gapi": "Raung", "ga_code": "RAU"},
    {"ga_nama_gapi": "Rinjani", "ga_code": "RIN"},
    {"ga_nama_gapi": "Rokatenda", "ga_code": "ROK"},
    {"ga_nama_gapi": "Ruang", "ga_code": "RUA"},
    {"ga_nama_gapi": "Salak", "ga_code": "SAL"},
    {"ga_nama_gapi": "Sangeangapi", "ga_code": "SAN"},
    {"ga_nama_gapi": "Semeru", "ga_code": "SMR"},
    {"ga_nama_gapi": "Seulawah Agam", "ga_code": "SEU"},
    {"ga_nama_gapi": "Sinabung", "ga_code": "SIN"},
    {"ga_nama_gapi": "Sirung", "ga_code": "SIR"},
    {"ga_nama_gapi": "Slamet", "ga_code": "SLA"},
    {"ga_nama_gapi": "Soputan", "ga_code": "SOP"},
    {"ga_nama_gapi": "Sorikmarapi", "ga_code": "SOR"},
    {"ga_nama_gapi": "Sumbing", "ga_code": "SBG"},
    {"ga_nama_gapi": "Sundoro", "ga_code": "SUN"},
    {"ga_nama_gapi": "Talang", "ga_code": "TAL"},
    {"ga_nama_gapi": "Tambora", "ga_code": "TAM"},
    {"ga_nama_gapi": "Tandikat", "ga_code": "TAN"},
    {"ga_nama_gapi": "Tangkoko", "ga_code": "TGK"},
    {"ga_nama_gapi": "Tangkuban Parahu", "ga_code": "TPR"},
    {"ga_nama_gapi": "Wurlali", "ga_code": "WUR"}
]

def generate_condition_queries_for_all_volcanoes(volcano_data):
    """Generate condition queries for all volcanoes from MAGMA API data"""
    
    condition_queries = []
    
    question_patterns = [
        "bagaimana kondisi {}",
        "bagaimana kondisi gunung {}",
        "bagaimana keadaan {}",
        "bagaimana keadaan gunung {}",
        "bagaimana situasi {}",
        "bagaimana situasi gunung {}",
        "apa kondisi {}",
        "apa kondisi gunung {}",
        "apa keadaan {}",
        "apa keadaan gunung {}",
        "gimana kondisi {}",
        "gimana kondisi gunung {}",
        "gimana keadaan {}",
        "gimana keadaan gunung {}",
        "how is {} condition",
        "how is mount {} condition",
        "what is {} status",
        "what is mount {} status",
        "{} kondisi bagaimana",
        "gunung {} kondisi bagaimana",
        "{} keadaan bagaimana",
        "gunung {} keadaan bagaimana",
    ]
    
    for volcano in volcano_data:
        name = volcano["ga_nama_gapi"].lower()
        simple_name = name.replace("gunung ", "").replace("mount ", "")
        
        for pattern in question_patterns:
            condition_queries.append(pattern.format(name))
            condition_queries.append(pattern.format(simple_name))
            
            # Add with question marks
            condition_queries.append(pattern.format(name) + "?")
            condition_queries.append(pattern.format(simple_name) + "?")
            
            # Add "saat ini" (now) variations
            condition_queries.append(pattern.format(name) + " saat ini")
            condition_queries.append(pattern.format(name) + " sekarang")
            condition_queries.append(pattern.format(name) + " skrg")
            condition_queries.append(pattern.format(simple_name) + " saat ini")
            condition_queries.append(pattern.format(simple_name) + " sekarang")
            condition_queries.append(pattern.format(simple_name) + " skrg")
            
            # Add "hari ini" (today) variations
            condition_queries.append(pattern.format(name) + " hari ini")
            condition_queries.append(pattern.format(simple_name) + " hari ini")
            
            # Add "terbaru" (latest) variations
            condition_queries.append(pattern.format(name) + " terbaru")
            condition_queries.append(pattern.format(simple_name) + " terbaru")
    
    return list(set(condition_queries))

TYPO_VARIANTS = {
    "indonesia": ["indonesioa", "indonedia", "indonrsia", "indonasia"],
    "gunung": ["gunung", "gunng", "gunugn"],
    "api": ["api", "ap i"],
    "berapa": ["berapa", "brapa", "berpa"],
}

def generate_typo_count_examples():
    base_templates = [
        "ada berapa gunung api di indonesia",
        "berapa jumlah gunung api di indonesia",
        "berapa banyak gunung api di indonesia",
    ]

    typo_examples = []

    for template in base_templates:
        for indo in TYPO_VARIANTS["indonesia"]:
            typo_examples.append(template.replace("indonesia", indo))

        for brp in TYPO_VARIANTS["berapa"]:
            typo_examples.append(template.replace("berapa", brp))

        for gng in TYPO_VARIANTS["gunung"]:
            typo_examples.append(template.replace("gunung", gng))

    return list(set(typo_examples))

# ======================================================
# Data Preparation from your intent classifier
# ======================================================
def generate_training_data_from_patterns():
    """
    Generate training data based on the patterns from your intent classifier
    """
    # Define intents based on your classifier
    intents = [
        "greeting",
        "identity",
        "capability",
        "general_chat",
        "location_required",
        "technical",
        "count_list_query",
        "status", 
        "out_of_scope"
    ]
    
    # Generate examples for each intent
    training_data = []
    
    # 1. Greeting examples
    greeting_examples = [
        "halo",
        "hai",
        "hello",
        "hi",
        "hey",
        "selamat pagi",
        "selamat siang",
        "selamat sore",
        "selamat malam",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "assalamualaikum",
        "salam",
        "permisi",
        "excuse me",
        "hai apa kabar",
        "halo selamat pagi",
        "hi admin",
        "hello kak",
        "hai pak",
        "selamat malam mbak",
        "halo selamat sore",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "morning",
        "afternoon",
        "evening",
        "night",
        "hi there",
        "hello there",
        "hey there",
        "greetings",
        "wassup",
        "what's up",
        "hi admin",
        "hello sir",
        "hello madam",
        "hi boss",
        "hello friend",
        "halo good morning",
        "hi selamat pagi",
        "apakabar magma"
    ]
    training_data.extend([(text, "greeting") for text in greeting_examples])
    greeting_entities = [
    "magma",
    "esdm",
    "admin",
    "kak",
    "pak",
    "mbak",
    ]

    base_greetings = ["halo", "hai", "hi", "hello", "hey"]

    for g in base_greetings:
        for e in greeting_entities:
            training_data.append((f"{g} {e}", "greeting"))

    # 2. Identity examples
    identity_examples = [
        "siapa kamu",
        "kamu siapa",
        "who are you",
        "what are you",
        "kamu ini siapa",
        "nama kamu",
        "your name",
        "anda siapa",
        "siapa namamu",
        "identitas kamu",
        "kamu dari mana",
        "kamu bekerja dimana",
        "kamu bagian dari siapa",
        "kamu asisten dari siapa",
        "siapa yang membuat kamu",
        "who are you",
        "what are you",
        "your name",
        "what's your name",
        "tell me about yourself",
        "who created you",
        "what is your identity",
        "introduce yourself",
        "tell me who you are",
        "what do you call yourself",
        "may i know who you are",
        "could you tell me about yourself",
        "what should i call you",
    ]
    training_data.extend([(text, "identity") for text in identity_examples])
    
    # 3. Capability examples
    capability_examples = [
        "apa yang bisa kamu lakukan",
        "apa yang dapat kamu bantu",
        "what can you do",
        "bantuan apa yang kamu berikan",
        "fungsi kamu",
        "your function",
        "kamu bisa apa",
        "kamu bisa bantu apa",
        "bisa bantu apa",
        "apa saja layanan kamu",
        "fitur apa yang ada",
        "kemampuan kamu apa",
        "apa yang kamu lakukan",
        "kamu mampu apa",
        "layanan apa yang tersedia",
        "kamu bisa lakukann apa",  # With typo
        "apa yg bisa kamu lakuin",  # With typo
        "kamu bisa apa aja",
        "apa aja yang bisa kamu bantu",
        "what can you do",
        "what are your capabilities",
        "what functions do you have",
        "what services do you provide",
        "how can you help me",
        "what assistance can you provide",
        "tell me your functions",
        "what are your features",
        "what do you offer",
        "how can you assist me",
        "what is your purpose",
        "what is your role",
        "could you tell me what you can do",
        "please explain your capabilities",
        "i'd like to know what you can help with",
    ]
    training_data.extend([(text, "capability") for text in capability_examples])
    
    # 4. General chat examples
    general_chat_examples = [
        "apa kabar",
        "how are you",
        "terima kasih",
        "thank you",
        "thanks",
        "sama-sama",
        "you're welcome",
        "bagus",
        "mantap",
        "keren",
        "nice",
        "great",
        "awesome",
        "good job",
        "makasih ya",
        "terimakasih banyak",
        "baik sekali",
        "sangat membantu",
        "terima kasih banyak",
        "apakabar hari ini",  # Without space
        "gimana kabarnya",
        "baik baik saja",
        "baik terima kasih",
         "thank you",
        "thanks",
        "thank you very much",
        "thanks a lot",
        "much appreciated",
        "appreciate it",
        "you're welcome",
        "my pleasure",
        "no problem",
        "how are you",
        "how are you doing",
        "how's it going",
        "what's up",
        "good",
        "great",
        "awesome",
        "fantastic",
        "wonderful",
        "excellent",
        "nice job",
        "well done",
        "good work",
        "terima kasih atas informasi tentang gunung",
        "terima kasih atas bantuan dengan informasi gunung",
        "thanks for the volcano information",
        "thank you for the earthquake data",
        "appreciate the geological hazard info",
    ]
    training_data.extend([(text, "general_chat") for text in general_chat_examples])
    
    # 5. Location required examples
    location_required_examples = [
        "apakah saya aman",
        "apakah daerah saya bahaya",
        "posisi saya aman atau tidak",
        "lokasi saya rawan bencana",
        "apakah wilayah saya aman",
        "tempat saya apakah bahaya",
        "apakah anda tau lokasi saya sekarang"
        "am i safe",
        "is my area safe",
        "is my location dangerous",
        "apakah aku dalam bahaya",
        "apakah kami aman disini",
        "daerah saya apakah rawan",
        "wilayah saya bagaimana",
        "posisi saya sekarang aman",
        "apakah tempat tinggal saya aman",
        "am i safe",
        "is my area safe",
        "is my location dangerous",
        "is it safe here",
        "am i in danger",
        "is this location safe",
        "am i at risk",
        "is my position safe",
        "how safe is my location",
        "am i in a safe zone",
        "is this area dangerous",
        "could you tell me if i'm safe",
        "please check if my location is safe",
        "is it safe where i am",
    ]
    training_data.extend([(text, "location_required") for text in location_required_examples])
    
    # 6. Count/list query examples
    count_list_examples = [
        "ada berapa gunung api",
        "berapa banyak gunung berapi",
        "berapa jumlah gunung aktif",
        "how many volcanoes",
        "ada berapa gunung api di indonesia",
        "jumlah gunung api di indonesia",
        "berapa gunung berapi di indonesia",
        "berapa banyak gunung di indonesia",
        "how many volcanoes",
        "how many volcanoes are there",
        "which volcanoes are active",
        "list of volcanoes",
        "list the volcanoes",
        "number of volcanoes",
        "total volcanoes",
        "count of volcanoes",
        "volcano count",
        "sebutkan daftar gunung api",
        "list gunung di indonesia",
        "berapa jumlah total gunung",
    ]
    count_list_examples.extend(generate_typo_count_examples())

    training_data.extend(
        [(text, "count_list_query") for text in count_list_examples]
    )
    
    # 7. Out of scope examples
    out_of_scope_examples = [
        "bagaimana cuaca besok",
        "weather tomorrow jakarta",
        "ramalan cuaca bandung",
        "cuaca di surabaya",
        "amerika serikat",
        "jepang bagaimana",
        "thailand aman tidak",
        "petir menyambar",
        "tornado terjadi",
        "banjir jakarta",
        "politik indonesia",
        "ekonomi bagaimana",
        "olahraga sepak bola",
        "hiburan musik",
        "kesehatan jantung",
        "covid 19",
        "makanan enak",
        "teknologi komputer",
        "sejarah indonesia",
        "matematika sulit",
        "bahlil lahirlah",
        "jokowi presiden",
        "prabowo bagaimana",
        "menurut kamu politik",
        "menurut anda ekonomi",
        "bahlil lahirlah",
        "jokowi presiden",
        "prabowo bagaimana",
        "anies baswedan",
        "ganjar pranowo",
        "mnurut mu bahlil gimana",
        "mnurut mu jokowi gimana",
        "bisakah anda prediksi tornado"
        
    ]
    training_data.extend([(text, "out_of_scope") for text in out_of_scope_examples])
    
    # 8. Technical examples (geological questions)
    technical_examples = [
        # ================= VOLCANO-RELATED QUERIES =================
        # Status queries for ALL Indonesian volcanoes from your data
        "gunung apa saja yang aktif",
        "gunung apa yang sedang erupsi",
        "ada gunung apa yang meletus hari ini",
        "info gunung aktif terbaru",
        "apakah jogja aman dari merapi",
        "kondisi keamanan yogyakarta saat ini",
        "bahaya merapi untuk sleman",
        "radius aman jogja",
        "status gunung agung",
        "status gunung ambang",
        "status gunung anak krakatau",
        "status gunung anak ranakah",
        "status gunung arjuno welirang",
        "status gunung awu",
        "status gunung banda api",
        "status gunung batur",
        "status gunung batutara",
        "status gunung bromo",
        "status gunung bur ni telong",
        "status gunung ciremai",
        "status gunung colo",
        "status gunung dempo",
        "status gunung dieng",
        "status gunung dukono",
        "status gunung ebulobo",
        "status gunung egon",
        "status gunung galunggung",
        "status gunung gamalama",
        "status gunung gamkonora",
        "status gunung gede",
        "status gunung guntur",
        "status gunung hobal",
        "status gunung ibu",
        "status gunung ijen",
        "status gunung ile werung",
        "status gunung ili boleng",
        "status gunung ili lewotolok",
        "status gunung inielika",
        "status gunung inierie",
        "status gunung iya",
        "status gunung kaba",
        "status gunung karangetang",
        "status gunung kelimutu",
        "status gunung kelud",
        "status gunung kerinci",
        "status gunung kie besi",
        "status gunung lamongan",
        "status gunung lereboleng",
        "status gunung lewotobi laki laki",
        "status gunung lewotobi perempuan",
        "status gunung lokon",
        "status gunung mahawu",
        "status gunung marapi",
        "status gunung merapi",
        "status gunung papandayan",
        "status gunung peut sague",
        "status gunung raung",
        "status gunung rinjani",
        "status gunung rokatenda",
        "status gunung ruang",
        "status gunung salak",
        "status gunung sangeangapi",
        "status gunung semeru",
        "status gunung seulawah agam",
        "status gunung sinabung",
        "status gunung sirung",
        "status gunung slamet",
        "status gunung soputan",
        "status gunung sorikmarapi",
        "status gunung sumbing",
        "status gunung sundoro",
        "status gunung talang",
        "status gunung tambora",
        "status gunung tandikat",
        "status gunung tangkoko",
        "status gunung tangkuban parahu",
        "status gunung wurlali",
        
        # Activity queries for specific volcanoes
        "aktivitas gunung agung",
        "aktivitas gunung anak krakatau",
        "aktivitas gunung merapi",
        "aktivitas gunung semeru",
        "aktivitas gunung sinabung",
        "aktivitas gunung bromo",
        "aktivitas gunung kelud",
        "aktivitas gunung rinjani",
        "aktivitas gunung gamalama",
        "aktivitas gunung dukono",
        "aktivitas vulkanik",
        "volcanic activity",
        
        # Danger/Warning queries
        "apakah gunung agung berbahaya",
        "apakah gunung anak krakatau perlu diwaspadai",
        "apakah gunung merapi aman",
        "apakah gunung semeru berbahaya",
        "apakah gunung sinabung perlu diwaspadai",
        "apakah gunung bromo aman dikunjungi",
        "apakah gunung kelud aktif",
        "apakah gunung rinjani berbahaya",
        "bahaya gunung api",
        "danger volcano",
        "ancaman letusan gunung",
        "volcano eruption threat",
        "apakah lokasi di yogyakarta aman",
        "apakah lokasi di jakarta aman",
        "apakah lokasi di medan aman",
        "apakah lokasi di surabaya aman",
        
        # Eruption history queries
        "kapan letusan terakhir gunung agung",
        "kapan letusan terakhir gunung anak krakatau",
        "kapan letusan terakhir gunung merapi",
        "kapan letusan terakhir gunung semeru",
        "kapan letusan terakhir gunung sinabung",
        "kapan letusan terakhir gunung kelud",
        "kapan letusan terakhir gunung bromo",
        "kapan letusan terakhir gunung rinjani",
        "erupsi besar gunung agung",
        "major eruption mount agung",
        "letusan 2010 gunung merapi",
        "merapi 2010 eruption",
        "letusan 2021 gunung semeru",
        "semeru 2021 eruption",
        
        # Specific volcano features
        "kawah gunung bromo",
        "bromo crater",
        "danau kawah gunung rinjani",
        "rinjani crater lake",
        "segara anak gunung rinjani",
        "segara anak lake",
        "kawah ijen blue fire",
        "ijen blue fire",
        "sulfur gunung ijen",
        "ijen sulfur",
        "awan panas gunung merapi",
        "merapi pyroclastic flow",
        "lava pijar gunung semeru",
        "semeru glowing lava",
        
        # Volcano monitoring terms
        "status var gunung merapi",
        "merapi var status",
        "status ven gunung semeru",
        "semeru ven status",
        "vona gunung agung",
        "agung vona",
        "peringatan gunung api level 1",
        "volcano alert level 1",
        "peringatan gunung api level 2",
        "volcano alert level 2",
        "peringatan gunung api level 3",
        "volcano alert level 3",
        "siaga gunung api",
        "volcano standby",
        "waspada gunung api",
        "volcano caution",
        
        # ================= EARTHQUAKE-RELATED QUERIES =================
        "gempa bumi hari ini",
        "earthquake today",
        "gempabumi terbaru",
        "latest earthquake",
        "gempa di sumatera",
        "earthquake in sumatra",
        "gempa di jawa",
        "earthquake in java",
        "gempa di sulawesi",
        "earthquake in sulawesi",
        "gempa di maluku",
        "earthquake in maluku",
        "gempa di papua",
        "earthquake in papua",
        "gempa di bali",
        "earthquake in bali",
        "gempa di lombok",
        "earthquake in lombok",
        "gempa di flores",
        "earthquake in flores",
        
        # Earthquake magnitude queries
        "gempa magnitudo 5.0",
        "earthquake magnitude 5.0",
        "gempa magnitudo 6.0",
        "earthquake magnitude 6.0",
        "gempa magnitudo 7.0",
        "earthquake magnitude 7.0",
        "gempa skala richter",
        "earthquake richter scale",
        "gempa dangkal",
        "shallow earthquake",
        "gempa dalam",
        "deep earthquake",
        
        # Historical earthquakes
        "gempa aceh 2004",
        "aceh earthquake 2004",
        "gempa yogya 2006",
        "yogyakarta earthquake 2006",
        "gempa padang 2009",
        "padang earthquake 2009",
        "gempa palu 2018",
        "palu earthquake 2018",
        "gempa lombok 2018",
        "lombok earthquake 2018",
        
        # ================= TSUNAMI-RELATED QUERIES =================
        "tsunami warning",
        "peringatan tsunami",
        "gelombang tsunami",
        "tsunami wave",
        "potensi tsunami",
        "tsunami potential",
        "ancaman tsunami",
        "tsunami threat",
        "tsunami aceh 2004",
        "aceh tsunami 2004",
        "tsunami selat sunda 2018",
        "sunda strait tsunami 2018",
        "tsunami palu 2018",
        "palu tsunami 2018",
        
        # ================= LANDSLIDE-RELATED QUERIES =================
        "longsor tanah",
        "landslide",
        "tanah longsor",
        "gerakan tanah",
        "ground movement",
        "longsor di bogor",
        "landslide in bogor",
        "longsor di jawa barat",
        "landslide in west java",
        "longsor di sumatera",
        "landslide in sumatra",
        "longsor di kalimantan",
        "landslide in kalimantan",
        "longsor di sulawesi",
        "landslide in sulawesi",
        
        # ================= MAGMA API SPECIFIC QUERIES =================
        "data magma esdm",
        "magma esdm data",
        "api magma esdm",
        "magma esdm api",
        "pvmbg update",
        "pvmbg data",
        "data gunung api pvmbg",
        "pvmbg volcano data",
        "var status pvmbg",
        "pvmbg var status",
        "ven status pvmbg",
        "pvmbg ven status",
        "vona terbaru pvmbg",
        "pvmbg latest vona",
        
        # ================= LOCATION-BASED QUERIES =================
        "gunung api di bali",
        "volcanoes in bali",
        "gunung api di jawa",
        "volcanoes in java",
        "gunung api di sumatera",
        "volcanoes in sumatra",
        "gunung api di sulawesi",
        "volcanoes in sulawesi",
        "gunung api di nusa tenggara",
        "volcanoes in nusa tenggara",
        "gunung api di maluku",
        "volcanoes in maluku",
        "gunung api di papua",
        "volcanoes in papua",
        
        # ================= COMPARISON QUERIES =================
        "gunung mana yang paling aktif",
        "which volcano is most active",
        "gunung mana yang paling berbahaya",
        "which volcano is most dangerous",
        "gunung mana yang tertinggi",
        "which volcano is tallest",
        "perbandingan gunung merapi dan semeru",
        "comparison merapi and semeru",
        
        # ================= TIME-BASED QUERIES =================
        "aktivitas gunung api bulan ini",
        "volcano activity this month",
        "letusan gunung tahun 2023",
        "volcano eruptions 2023",
        "gempa bumi minggu ini",
        "earthquakes this week",
        "longsor tahun 2024",
        "landslides 2024",
        
        # ================= SAFETY & MITIGATION =================
        "jarak aman dari gunung api",
        "safe distance from volcano",
        "zona bahaya gunung api",
        "volcano danger zone",
        "evakuasi gunung api",
        "volcano evacuation",
        "mitigasi bencana gunung api",
        "volcano disaster mitigation",
        "keselamatan gunung api",
        "volcano safety",
        
        # ================= TECHNICAL TERMS =================
        "deformasi gunung api",
        "volcano deformation",
        "aktivitas seismik",
        "seismic activity",
        "aktivitas hidrotermal",
        "hydrothermal activity",
        "gas gunung api",
        "volcano gas",
        "abu vulkanik",
        "volcanic ash",
        "lava",
        "magma",
        "kubah lava",
        "lava dome",
        "aliran piroklastik",
        "pyroclastic flow",
        "awan panas",
        "hot cloud",
        "lahar",
        "volcanic mudflow",
        
        # ================= QUANTITY QUERIES =================
        "berapa banyak gunung api di indonesia",
        "how many volcanoes in indonesia",
        "berapa gunung api yang aktif",
        "how many active volcanoes",
        "berapa gunung api level siaga",
        "how many volcanoes on alert",
        "berapa gunung api yang meletus",
        "how many erupting volcanoes",
        
        # ================= QUESTION PATTERNS =================
        "bagaimana kondisi gunung agung",
        "how is mount agung condition",
        "apa status gunung merapi",
        "what is merapi status",
        "apakah gunung semeru aktif",
        "is semeru volcano active",
        "kapan terakhir letusan gunung kelud",
        "when was kelud last eruption",
        "dimana lokasi gunung rinjani",
        "where is rinjani location",
        "berapa tinggi gunung semeru",
        "how tall is semeru",
        "mengapa gunung merapi sering meletus",
        "why does merapi often erupt",
        "siapa yang memantau gunung api",
        "who monitors volcanoes",
        "gunung apa saja yang sedang aktif saat ini",
        "which volcanoes are currently active",
        
        # ================= MIXED LANGUAGE QUERIES =================
        "status volcano merapi",
        "activity gunung semeru",
        "eruption gunung sinabung",
        "condition mount agung",
        "alert level gunung bromo",
        "data gempa earthquake",
        "tsunami warning peringatan",
        "landslide tanah longsor",
        
        # ================= SHORT FORM QUERIES =================
        "gnung agung",
        "gnung merapi",
        "gnung semeru",
        "gpa bumi",
        "tsnmi",
        "lgsr",
        "aktifitas gnung",
        "status gn api",
        
        # ================= NUMBERS WITH QUERIES =================
        "status 2024",
        "gempa 2023",
        "letusan 2022",
        "tsunami 2004",
        "longsor 2021",
        "gunung api 127",
        "earthquake 6.5",
        "magnitude 7.0",
        "Bagaimana kondisi gunungapi di Indonesia saat ini?",
        "Bagaimana status gunungapi di Indonesia saat ini?"

    ]
    # volcano_condition_queries = generate_condition_queries_for_all_volcanoes(volcano_data)
    # technical_examples.extend(volcano_condition_queries)
    
    # training_data = [(text, "technical") for text in technical_examples]
    # training_data.extend([(text, "technical") for text in volcano_condition_queries])
    training_data.extend([(text, "technical") for text in technical_examples])
    
    status_examples = [
        # Indonesian
        "status gunung api apa saja",
        "status gunung api ada apa saja sih",
        "apa saja status level gunung api",
        "status gunung api ada berapa level",
        "level status gunung api",
        "tingkatan status gunung api",
        "apa itu level gunung api",
        "jenis status gunung api",
        "tingkat kewaspadaan gunung api apa saja",
        "kondisi gunungapi",
        "status gunungapi",
        
        # English
        "volcano status levels",
        "what are volcano alert levels",
        "how many volcano alert levels",
        "types of volcano status",
        "volcano alert categories",
    ]

    training_data.extend([(text, "status") for text in status_examples])
    training_data.extend([
        ("apa status gunung api sekarang", "technical"),
        ("apa status gunung api saat ini", "technical"),
        ("apa saja status gunung api", "status"),
    ])
    return training_data


# ======================================================
# Text cleaning function
# ======================================================
def clean_text(text):
    """Clean text by removing punctuation and normalizing"""
    if not isinstance(text, str):
        text = str(text)
    # Remove punctuation but keep letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', '', text)
    # Lowercase
    text = text.lower()
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ======================================================
# Data Augmentation Functions
# ======================================================
def typo_augment(text, prob=0.15):
    """Introduce typos in text"""
    if len(text) < 4 or random.random() > prob:
        return text

    i = random.randint(1, len(text) - 2)
    op = random.choice(["delete", "swap", "repeat"])

    if op == "delete":
        return text[:i] + text[i + 1:]

    if op == "swap":
        return text[:i - 1] + text[i] + text[i - 1] + text[i + 1:]

    if op == "repeat":
        return text[:i] + text[i] + text[i:]

    return text

def short_augment(text):
    """Create shorter versions of text"""
    words = text.split()
    if len(words) <= 1:
        return text
    cut = random.randint(1, len(words) - 1)
    return " ".join(words[:cut])

def punctuation_augment(text, prob=0.3):
    """Add/remove punctuation variations"""
    variations = [text]
    
    if random.random() < prob:
        # Add question mark if not present
        if '?' not in text:
            variations.append(text + '?')
    
    if random.random() < prob:
        # Add period if not present
        if '.' not in text and '?' not in text and '!' not in text:
            variations.append(text + '.')
    
    if random.random() < prob:
        # Add comma in the middle (if long enough)
        words = text.split()
        if len(words) >= 3:
            insert_pos = random.randint(1, len(words) - 1)
            words_with_comma = words[:insert_pos] + [words[insert_pos] + ','] + words[insert_pos + 1:]
            variations.append(' '.join(words_with_comma))
    
    return variations

def greeting_augment(text, label):
    """Special augmentation for greetings"""
    if label != "greeting":
        return [text]
    
    variations = [text]
    
    # Check if it's a time-based greeting
    time_keywords = ['pagi', 'siang', 'sore', 'malam']
    if any(keyword in text.lower() for keyword in time_keywords):
        for time in time_keywords:
            if time not in text.lower():
                # Add missing time greetings
                if 'selamat' in text.lower():
                    variations.append(f"selamat {time}")
                else:
                    variations.append(f"selamat {time}")
    
    # Add/remove honorifics
    honorifics = ['kak', 'admin', 'pak', 'bu', 'mas', 'mbak']
    for honorific in honorifics:
        if honorific in text.lower():
            # Remove honorific
            cleaned = text.lower().replace(honorific, '').strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if cleaned:
                variations.append(cleaned)
        else:
            # Add honorific
            variations.append(f"{text} {honorific}")
    
    return variations

def synonym_augment(text, label):
    """Replace words with synonyms"""
    if label not in ["greeting", "capability", "identity", "general_chat"]:
        return [text]
    
    synonyms_map = {
        'apa': ['apa saja', 'manakah', 'apakah'],
        'siapa': ['siapakah', 'siapa gerangan'],
        'berapa': ['jumlah', 'total', 'berapa banyak'],
        'aktif': ['erupsi', 'meletus', 'siaga', 'waspada'],
        'lokasi': ['daerah', 'wilayah', 'tempat', 'posisi'],
        'aman': ['kondusif', 'tidak bahaya', 'safe'],
        'bisa': ['dapat', 'mampu'],
        'kamu': ['anda', 'kalian'],
        'lakukan': ['kerjakan', 'buat', 'tanggung'],
        'fungsi': ['tugas', 'peran', 'kegunaan'],
        'nama': ['sebutan', 'panggilan'],
        'halo': ['hai', 'hei'],
        'selamat': ['salam'],
        'tanya': ['bertanya', 'bertanya-tanya'],
        'ingin': ['mau', 'hendak'],
        'bantu': ['tolong', 'bantuan'],
        'terima kasih': ['makasih', 'terimakasih'],
        'bagus': ['baik', 'mantap', 'keren'],
        'status': ['kondisi', 'keadaan'],
        'gunung': ['gunung api', 'volcano'],
        'gempa': ['gempabumi', 'earthquake'],
        'bahaya': ['berbahaya', 'rawan'],
    }
    
    words = text.lower().split()
    augmented = []
    
    # Try to replace each word with synonym
    for i, word in enumerate(words):
        if word in synonyms_map:
            for synonym in synonyms_map[word]:
                new_words = words.copy()
                new_words[i] = synonym
                augmented.append(' '.join(new_words))
    
    return augmented if augmented else [text]

# ======================================================
# Save training configuration
# ======================================================
def save_training_config():
    config = {
        "timestamp": TIMESTAMP,
        "seed": SEED,
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "xgb_params": {
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "mlogloss"
        },
        "ocsvm_params": {
            "kernel": "rbf",
            "nu": 0.25,
            "gamma": "scale"
        },
        "augmentation": {
            "typo_prob": 0.15,
            "short_augment": True,
            "punctuation_prob": 0.3,
            "synonym_augment": True,
            "greeting_augment": True
        },
        "text_cleaning_function": "clean_text",
        "intents": [
            "greeting",
            "identity", 
            "capability",
            "general_chat",
            "location_required",
            "technical",
            "count_list_query",
            "out_of_scope"
        ]
    }
    
    config_path = os.path.join(LOGS_DIR, f"training_config_{TIMESTAMP}.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config_path

# ======================================================
# Save augmented dataset
# ======================================================
def save_augmented_dataset(aug_texts, aug_labels):
    aug_df = pd.DataFrame({
        'text': aug_texts,
        'label': aug_labels
    })
    
    aug_csv_path = os.path.join(LOGS_DIR, f"augmented_dataset_{TIMESTAMP}.csv")
    aug_df.to_csv(aug_csv_path, index=False, encoding='utf-8')
    
    # Also save sample of augmented data
    sample_df = aug_df.sample(min(50, len(aug_df)))
    sample_path = os.path.join(LOGS_DIR, f"augmented_sample_{TIMESTAMP}.csv")
    sample_df.to_csv(sample_path, index=False, encoding='utf-8')
    
    return aug_csv_path, sample_path

# ======================================================
# Save model metadata
# ======================================================
def save_model_metadata(encoder, X_shape, aug_texts_count):
    metadata = {
        "timestamp": TIMESTAMP,
        "classes": encoder.classes_.tolist(),
        "num_classes": len(encoder.classes_),
        "embedding_dim": X_shape[1],
        "total_samples": X_shape[0],
        "augmented_samples": aug_texts_count,
        "model_files": {
            "intent_classifier": "intent_xgb.joblib",
            "label_encoder": "intent_encoder.joblib",
            "out_of_scope_detector": "intent_occ.joblib",
            "embedder_info": "intent_embedder_info.joblib"
        },
        "text_cleaning": {
            "function": "clean_text",
            "description": "Removes punctuation, lowercases, removes extra spaces"
        },
        "intent_descriptions": {
            "greeting": "User is greeting the assistant",
            "identity": "User asks who/what the assistant is", 
            "capability": "User asks what the assistant can do",
            "general_chat": "General conversation (thank you, how are you, etc.)",
            "location_required": "Question needs user's location",
            "technical": "Technical geological question (default)",
            "count_list_query": "Asking for count or list of volcanoes",
            "out_of_scope": "Question outside MAGMA's geological expertise"
        }
    }
    
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return metadata_path

# ======================================================
# Inference Module (to replace your original classifier)
# ======================================================
class MAGMAIntentClassifier:
    """Trained intent classifier for MAGMA Assistant"""
    
    def __init__(self, model_dir=None):
        """Load trained models"""
        if model_dir is None:
            model_dir = MODELS_DIR
        
        # Load models
        self.intent_model = joblib.load(os.path.join(model_dir, "intent_xgb.joblib"))
        self.encoder = joblib.load(os.path.join(model_dir, "intent_encoder.joblib"))
        self.out_of_scope_model = joblib.load(os.path.join(model_dir, "intent_occ.joblib"))
        embedder_info = joblib.load(os.path.join(model_dir, "intent_embedder_info.joblib"))
        
        # Initialize embedder
        self.embedder = TextEmbedding(model_name=embedder_info["model_name"])
        
        # Load metadata
        metadata_path = os.path.join(model_dir, "model_metadata.json")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
    
    def clean_text(self, text: str) -> str:
        """Clean input text"""
        return clean_text(text)
    
    def predict(self, user_input: str, geo_location=None) -> Dict[str, Any]:
        """
        Predict intent for user input
        
        Returns:
            Dictionary with prediction results
        """
        # Clean text
        cleaned_text = self.clean_text(user_input)
        
        # Generate embedding
        embedding = list(self.embedder.embed([cleaned_text]))[0].flatten()
        X = np.array([embedding])

        probs = self.intent_model.predict_proba(X)[0]
        max_prob = np.max(probs)

        
        # First check if out of scope
        is_out_of_scope = self.out_of_scope_model.predict(X)[0] == -1
        # Predict intent
        proba = self.intent_model.predict_proba(X)[0]
        pred_idx = np.argmax(proba)
        confidence = proba[pred_idx]
        intent = self.encoder.inverse_transform([pred_idx])[0]
        
        if max_prob > 0.7:
            final_intent = intent
        elif is_out_of_scope:
            final_intent = "out_of_scope"
        else:
            final_intent = intent

        if final_intent == "out_of_scope":
            return {
                "status": "success",
                "intent": "out_of_scope",
                "confidence": 1.0,
                "requires_api": False,
                "cleaned_text": cleaned_text
            }
        
        
        # Special handling for location_required
        if final_intent == "location_required" and geo_location:
            final_intent = "technical"

            # if isinstance(geo_location, (list, tuple)) and len(geo_location) == 2:
            #     if geo_location[0] is not None and geo_location[1] is not None:
            #         # Has valid GPS data, treat as technical
            #         intent = "technical"
        
        return {
            "status": "success",
            "intent": final_intent,
            "confidence": float(confidence),
            "requires_api": final_intent == "technical",
            "cleaned_text": cleaned_text,
            "all_probabilities": {
                cls: float(prob) for cls, prob in zip(self.encoder.classes_, proba)
            }
        }
    
    def get_intent_description(self, intent: str) -> str:
        """Get description for an intent"""
        return self.metadata.get("intent_descriptions", {}).get(intent, "No description available")

# ======================================================
# Main Training Function
# ======================================================
def train_magma_intent_model():
    """
    Train the MAGMA intent classification model
    """
    print(f"Training MAGMA Intent Classifier")
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Save training configuration
    config_path = save_training_config()
    print(f"✓ Training configuration saved to: {config_path}")
    
    # ======================================================
    # Generate and prepare training data
    # ======================================================
    print("\n📊 Generating training data from patterns...")
    training_data = generate_training_data_from_patterns()
    
    # Convert to DataFrame
    df = pd.DataFrame(training_data, columns=['text', 'label'])
    
    # Clean the text data
    df['cleaned_text'] = df['text'].apply(clean_text)
    texts = df['cleaned_text'].tolist()
    labels = df['label'].astype(str).tolist()
    
    print(f"✓ Generated {len(texts)} training samples")
    print(f"  Sample cleaned texts: {texts[:3]}")
    print(f"  Labels distribution:")
    for label in set(labels):
        count = labels.count(label)
        print(f"    - {label}: {count} samples")
    
    # ======================================================
    # Augment dataset
    # ======================================================
    print("\n⚙️ Augmenting dataset...")
    aug_texts = []
    aug_labels = []
    
    for text, label in zip(texts, labels):
        # Add original cleaned text
        aug_texts.append(text)
        aug_labels.append(label)
        
        # Typo augmentation
        typo_text = typo_augment(text)
        aug_texts.append(typo_text)
        aug_labels.append(label)
        
        # Short augmentation
        short_text = short_augment(text)
        aug_texts.append(short_text)
        aug_labels.append(label)
        
        # Combined typo + short
        aug_texts.append(short_augment(typo_augment(text)))
        aug_labels.append(label)
        
        # Punctuation augmentation
        for punct_text in punctuation_augment(text):
            aug_texts.append(punct_text)
            aug_labels.append(label)
        
        # Greeting-specific augmentation
        for greeting_text in greeting_augment(text, label):
            aug_texts.append(greeting_text)
            aug_labels.append(label)
        
        # Synonym augmentation
        for synonym_text in synonym_augment(text, label):
            aug_texts.append(synonym_text)
            aug_labels.append(label)
    
    # Remove duplicates while preserving order
    unique_pairs = list(dict.fromkeys(zip(aug_texts, aug_labels)))
    aug_texts, aug_labels = zip(*unique_pairs) if unique_pairs else ([], [])
    
    print(f"✓ Augmented to {len(aug_texts)} unique samples")
    
    # Save augmented dataset
    aug_csv_path, sample_path = save_augmented_dataset(aug_texts, aug_labels)
    print(f"✓ Augmented dataset saved to: {aug_csv_path}")
    print(f"✓ Sample dataset saved to: {sample_path}")
    
    # ======================================================
    # FastEmbed Embedder
    # ======================================================
    print("\n⚙️ Generating embeddings...")
    embedder = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # Embed in batches for efficiency
    X_list = []
    batch_size = 32
    for i in range(0, len(aug_texts), batch_size):
        batch = aug_texts[i:i + batch_size]
        embeddings = list(embedder.embed(batch))
        X_list.extend([emb.flatten() for emb in embeddings])
    
    X = np.array(X_list)
    print(f"✓ Embeddings generated: {X.shape}")
    
    # ======================================================
    # Encode labels
    # ======================================================
    encoder = LabelEncoder()
    y = encoder.fit_transform(aug_labels)
    print(f"✓ Labels encoded")
    print(f"  Intents: {list(encoder.classes_)}")
    print(f"  Number of classes: {len(encoder.classes_)}")
    
    # ======================================================
    # Intent Classifier
    # ======================================================
    print("\n⚙️ Training Intent Classifier...")
    intent_model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=SEED,
        n_jobs=-1
    )
    
    intent_model.fit(X, y)
    print("✓ Intent classifier trained")
    
    # ======================================================
    # Out-of-Scope Detector
    # ======================================================
    print("\n⚙️ Training Out-of-Scope Detector...")
    occ = OneClassSVM(
        kernel="rbf",
        nu=0.25,
        gamma="scale"
    )
    occ.fit(X)
    print("✓ Out-of-scope detector trained")
    
    # ======================================================
    # Save models
    # ======================================================
    print("\n💾 Saving models...")
    
    # Save main models
    joblib.dump(intent_model, os.path.join(MODELS_DIR, "intent_xgb.joblib"))
    print(f"  ✓ Intent classifier saved to: {MODELS_DIR}/intent_xgb.joblib")
    
    joblib.dump(encoder, os.path.join(MODELS_DIR, "intent_encoder.joblib"))
    print(f"  ✓ Label encoder saved to: {MODELS_DIR}/intent_encoder.joblib")
    
    joblib.dump(occ, os.path.join(MODELS_DIR, "intent_occ.joblib"))
    print(f"  ✓ Out-of-scope detector saved to: {MODELS_DIR}/intent_occ.joblib")
    
    # Save embedder configuration
    embedder_info = {
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_dim": X.shape[1],
        "batch_size": 32
    }
    joblib.dump(embedder_info, os.path.join(MODELS_DIR, "intent_embedder_info.joblib"))
    print(f"  ✓ Embedder info saved to: {MODELS_DIR}/intent_embedder_info.joblib")
    
    # Save model metadata
    metadata_path = save_model_metadata(encoder, X.shape, len(aug_texts))
    print(f"  ✓ Model metadata saved to: {metadata_path}")
    
    # ======================================================
    # Test the trained model
    # ======================================================
    print("\n🧪 Testing the trained model...")
    classifier = MAGMAIntentClassifier(MODELS_DIR)
    
    test_cases = [
        "halo selamat pagi",
        "siapa kamu",
        "apa yang bisa kamu lakukan",
        "terima kasih banyak",
        "apakah saya aman",
        "status gunung merapi",
        "ada berapa gunung api",
        "bagaimana cuaca besok",
    ]
    
    print("  Test predictions:")
    for test in test_cases:
        result = classifier.predict(test)
        print(f"    '{test}' → {result['intent']} (confidence: {result['confidence']:.2f})")
    
    # ======================================================
    # Training Summary
    # ======================================================
    print(f"\n{'='*50}")
    print("✅ TRAINING COMPLETE")
    print(f"{'='*50}")
    print(f"📁 Output Structure:")
    print(f"  ├── {OUTPUT_DIR}/")
    print(f"  │   ├── models/         # Saved models")
    print(f"  │   └── logs/           # Training logs & configs")
    print(f"\n📊 Training Summary:")
    print(f"  ├── Original samples: {len(texts)}")
    print(f"  ├── Augmented samples: {len(aug_texts)}")
    print(f"  ├── Embedding dimension: {X.shape[1]}")
    print(f"  ├── Number of intents: {len(encoder.classes_)}")
    print(f"  └── Intents: {', '.join(encoder.classes_)}")
    print(f"\n🎯 To use the model:")
    print(f"  from magma_intent_model import MAGMAIntentClassifier")
    print(f"  classifier = MAGMAIntentClassifier()")
    print(f"  result = classifier.predict('halo selamat pagi')")
    print(f"\n⏰ Timestamp: {TIMESTAMP}")
    print(f"{'='*50}")
    
    return classifier

# ======================================================
# Integration with your original ResponseTemplates
# ======================================================
def integrate_with_response_templates():
    """
    Show how to integrate the trained model with your ResponseTemplates
    """
    # Load the trained model
    classifier = MAGMAIntentClassifier(MODELS_DIR)
    
    # Your original ResponseTemplates class (simplified for demo)
    class ResponseTemplates:
        @staticmethod
        def get_greeting_response():
            return "Halo! Saya MAGMA Indonesia, asisten virtual mitigasi bencana geologi."
        
        @staticmethod
        def get_identity_response():
            return "Saya adalah MAGMA Indonesia dari PVMBG, Badan Geologi, Kementerian ESDM."
        
        @staticmethod
        def get_capability_response():
            return "Saya dapat membantu dengan informasi aktivitas gunung api, gempa bumi, dan mitigasi bencana geologi."
        
        @staticmethod
        def get_general_chat_response(user_input):
            return "Terima kasih! Senang bisa membantu."
        
        @staticmethod
        def get_location_required_response():
            return "Untuk pertanyaan tentang keamanan lokasi, saya perlu informasi lokasi Anda."
        
        @staticmethod
        def get_out_of_scope_response():
            return "Maaf, keahlian saya terbatas pada informasi kebencanaan geologi di Indonesia."
        
        @staticmethod
        def get_count_list_response():
            return "Indonesia memiliki 127 gunung api aktif."
    
    def handle_user_query(user_input: str, geo_location=None):
        """Handle user query with trained intent classifier"""
        # Get intent prediction
        intent_result = classifier.predict(user_input, geo_location)
        
        # Map intent to response template
        intent = intent_result['intent']
        
        if intent == 'greeting':
            return ResponseTemplates.get_greeting_response()
        elif intent == 'identity':
            return ResponseTemplates.get_identity_response()
        elif intent == 'capability':
            return ResponseTemplates.get_capability_response()
        elif intent == 'general_chat':
            return ResponseTemplates.get_general_chat_response(user_input)
        elif intent == 'location_required':
            return ResponseTemplates.get_location_required_response()
        elif intent == 'out_of_scope':
            return ResponseTemplates.get_out_of_scope_response()
        elif intent == 'count_list_query':
            return ResponseTemplates.get_count_list_response()
        elif intent == 'technical':
            # This would go to your API pipeline
            return "Processing technical geological question..."
        else:
            return "Maaf, saya tidak memahami pertanyaan Anda."
    
    # Test integration
    print("\n🔗 Integration test with ResponseTemplates:")
    test_queries = [
        "halo",
        "siapa kamu",
        "apa yang bisa kamu lakukan",
        "terima kasih",
        "apakah daerah saya aman",
    ]
    
    for query in test_queries:
        response = handle_user_query(query)
        print(f"  Q: {query}")
        print(f"  A: {response}")
        print()

# ======================================================
# Main execution
# ======================================================
if __name__ == "__main__":
    # Train the model
    classifier = train_magma_intent_model()
    
    # Show integration with response templates
    integrate_with_response_templates()