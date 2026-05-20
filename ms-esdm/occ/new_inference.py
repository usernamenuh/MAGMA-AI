import sys
import os
import json
from typing import List, Dict, Any, Tuple
from responses import get_intent_response

# Add the parent directory to path to import the classifier
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from new_train import MAGMAIntentClassifier

esdm_test=[
    {
        "input": "Apakah posisi saya dalam bahaya sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "info gerakan tanah terakhir",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "apa yang kamu lakukann",
        "description": "Test case for capability",
        "expected_intent": "capability",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "halo",
        "description": "Test case for greeting",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Bagaimana status pergerakan tanah terdekat dengan saya?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Apakah wilayah saya rawan gempa bumi?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Gunung apa saja yang sedang aktif saat ini?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "kamu siapa?",
        "description": "Test case for identity",
        "expected_intent": "identity",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "bisakah anda prediksi tornado?",
        "description": "Test case for out_of_scope",
        "expected_intent": "out_of_scope",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "mnurut mu bahlil gimana?",
        "description": "Test case for out_of_scope",
        "expected_intent": "out_of_scope",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Hai apakabar?",
        "description": "Test case for greeting",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Apakah posisi saya dalam bahaya sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Apakah lokasi di yogyakarta aman?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Ada berapa gunung api di indonesia?",
        "description": "Test case for count_list_query",
        "expected_intent": "count_list_query",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Bagaimana status gunung sumeru?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Bagaimana kondisi aktivitas Gunung Sinabung sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Apakah aktivitas Gunung Anak Krakatau perlu diwaspadai?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Kapan erupsi besar terakhir Gunung Agung yang mengeluarkan awan panas guguran?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Gunung apa saja yang sedang aktif saat ini?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Apakah wilayah saya rawan gempa bumi?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "Bagaimana status pergerakan tanah terdekat dengan saya?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "kamu bisa apa saja",
        "description": "Test case for capability",
        "expected_intent": "capability",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "kapan letusan terakhir sumeru",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "status tanah longsor terdekat dengan saya",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "apakah anda tau lokasi saya sekarang?",
        "description": "Test case for location_required",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "hi magma?",
        "description": "Test case for greetings",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "halo magma?",
        "description": "Test case for greetings",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "input": "apakabar magma?",
        "description": "Test case for greetings",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    }
]

# ======================================================
# Test Cases
# ======================================================
test_cases = [
    # Category 1: Greetings - NORMAL VERSIONS ONLY
    {
        "input": "halo",
        "description": "Greeting - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hai",
        "description": "Greeting - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hello",
        "description": "Greeting - English normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hi",
        "description": "Greeting - English short normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "selamat pagi",
        "description": "Greeting with time - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "selamat siang",
        "description": "Greeting with time - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "selamat sore",
        "description": "Greeting with time - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "selamat malam",
        "description": "Greeting with time - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "good morning",
        "description": "Greeting - English time normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "good afternoon",
        "description": "Greeting - English time normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "good evening",
        "description": "Greeting - English time normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "assalamualaikum",
        "description": "Greeting - Islamic normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "salam",
        "description": "Greeting - short normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "permisi",
        "description": "Greeting - polite normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "excuse me",
        "description": "Greeting - English polite normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hai apa kabar",
        "description": "Greeting + how are you - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "halo selamat pagi",
        "description": "Double greeting - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hi admin",
        "description": "Greeting with honorific - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "hello kak",
        "description": "Greeting with honorific - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    
    # Category 2: Identity Questions - NORMAL VERSIONS ONLY
    {
        "input": "siapa kamu",
        "description": "Identity question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu siapa",
        "description": "Identity question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "who are you",
        "description": "Identity question - English normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "what are you",
        "description": "Identity question - English normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu ini siapa",
        "description": "Identity question - emphatic normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "nama kamu",
        "description": "Name question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "your name",
        "description": "Name question - English normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "anda siapa",
        "description": "Identity question - formal normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "siapa namamu",
        "description": "Name question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "identitas kamu",
        "description": "Identity question - formal normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu dari mana",
        "description": "Origin question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu bekerja dimana",
        "description": "Workplace question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu bagian dari siapa",
        "description": "Affiliation question - normal",
        "expected_intent": "identity",
        "geo_location": None
    },
    
    # Category 3: Capability Questions - NORMAL VERSIONS ONLY
    {
        "input": "apa yang bisa kamu lakukan",
        "description": "Capability question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "apa yang dapat kamu bantu",
        "description": "Help question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "what can you do",
        "description": "Capability question - English normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "bantuan apa yang kamu berikan",
        "description": "Help question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "fungsi kamu",
        "description": "Function question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "your function",
        "description": "Function question - English normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "kamu bisa apa",
        "description": "Capability question - short normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "kamu bisa bantu apa",
        "description": "Help question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "bisa bantu apa",
        "description": "Help question - short normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "apa saja layanan kamu",
        "description": "Services question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "fitur apa yang ada",
        "description": "Features question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "kemampuan kamu apa",
        "description": "Abilities question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "apa yang kamu lakukan",
        "description": "Actions question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "kamu mampu apa",
        "description": "Abilities question - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    
    # Category 4: Location-Required Questions - NORMAL VERSIONS ONLY (WITHOUT location)
    {
        "input": "apakah saya aman",
        "description": "Safety question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "apakah daerah saya bahaya",
        "description": "Area danger question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "daerah saya bahaya tidak",
        "description": "Area danger question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "posisi saya aman atau tidak",
        "description": "Position safety question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "lokasi saya rawan bencana",
        "description": "Location risk question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "apakah wilayah saya aman",
        "description": "Area safety question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "tempat saya apakah bahaya",
        "description": "Place danger question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "am i safe",
        "description": "Safety question - English normal without location",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "is my area safe",
        "description": "Area safety question - English normal without location",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "is my location dangerous",
        "description": "Location danger question - English normal without location",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "apakah aku dalam bahaya",
        "description": "Personal danger question without location - normal",
        "expected_intent": "location_required",
        "geo_location": None
    },
    
    # Category 5: Location-Required Questions (WITH location) - NORMAL VERSIONS ONLY
    {
        "input": "apakah saya aman",
        "description": "Safety question WITH valid GPS location - normal",
        "expected_intent": "technical",
        "geo_location": (-7.7956, 110.3695)  # Yogyakarta coordinates
    },
    {
        "input": "daerah saya rawan bencana",
        "description": "Disaster-prone question WITH location - normal",
        "expected_intent": "technical",
        "geo_location": (-6.2088, 106.8456)  # Jakarta coordinates
    },
    {
        "input": "apakah wilayah saya aman",
        "description": "Area safety question WITH location - normal",
        "expected_intent": "technical",
        "geo_location": (-7.2504, 112.7688)  # Surabaya coordinates
    },
    {
        "input": "lokasi saya apakah bahaya",
        "description": "Location danger question WITH location - normal",
        "expected_intent": "technical",
        "geo_location": (-6.9175, 107.6191)  # Bandung coordinates
    },
    {
        "input": "apakah posisi saya aman",
        "description": "Position safety question WITH location - normal",
        "expected_intent": "technical",
        # "geo_location": (-8.4095, 115.1889)  # Bali coordinates
    },
    
    # Category 6: Technical Geological Questions - NORMAL VERSIONS ONLY
    {
        "input": "status gunung merapi",
        "description": "Volcano status question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "status gunung semeru",
        "description": "Volcano status question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "status gunung sinabung",
        "description": "Volcano status question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "aktivitas gunung merapi",
        "description": "Volcano activity question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "aktivitas gunung semeru",
        "description": "Volcano activity question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "letusan gunung sinabung",
        "description": "Volcano eruption question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "erupsi gunung agung",
        "description": "Volcano eruption question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gempa bumi hari ini",
        "description": "Earthquake query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "earthquake terbaru",
        "description": "Earthquake query - English normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gempabumi sumatera",
        "description": "Earthquake location query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "tsunami warning",
        "description": "Tsunami warning query - English normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gelombang tsunami",
        "description": "Tsunami wave query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "longsor tanah",
        "description": "Landslide query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "landslide daerah",
        "description": "Landslide query - English normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gerakan tanah",
        "description": "Ground movement query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "tanah longsor bogor",
        "description": "Landslide location query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "bahaya geologi",
        "description": "Geological hazard query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "geological hazard",
        "description": "Geological hazard query - English normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "bencana gunung api",
        "description": "Volcano disaster query - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "disaster mitigation",
        "description": "Disaster mitigation query - English normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    
    # Category 7: Count/List Questions - NORMAL VERSIONS ONLY
    {
        "input": "ada berapa gunung api",
        "description": "Count question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "berapa banyak gunung berapi",
        "description": "Count question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "berapa jumlah gunung aktif",
        "description": "Count question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "how many volcanoes",
        "description": "Count question - English normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "apa saja gunung api aktif",
        "description": "List question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "mana saja gunung yang aktif",
        "description": "List question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "which volcanoes are active",
        "description": "List question - English normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "daftar gunung api",
        "description": "List question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "list of volcano",
        "description": "List question - English normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "sebutkan gunung api",
        "description": "List question - normal",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    
    # Category 8: General Chat - NORMAL VERSIONS ONLY
    {
        "input": "apa kabar",
        "description": "How are you - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "how are you",
        "description": "How are you - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "terima kasih",
        "description": "Thank you - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "thank you",
        "description": "Thank you - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "thanks",
        "description": "Thank you - English short normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "sama-sama",
        "description": "You're welcome - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "you're welcome",
        "description": "You're welcome - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "bagus",
        "description": "Praise - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "mantap",
        "description": "Praise - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "keren",
        "description": "Praise - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "nice",
        "description": "Praise - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "great",
        "description": "Praise - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "awesome",
        "description": "Praise - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "good job",
        "description": "Praise - English normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "makasih ya",
        "description": "Thanks with slang - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "terimakasih banyak",
        "description": "Thanks - formal normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "baik sekali",
        "description": "Praise - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "sangat membantu",
        "description": "Praise - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "terima kasih banyak",
        "description": "Thanks - emphatic normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    
    # Category 9: Out of Scope Questions - NORMAL VERSIONS ONLY
    {
        "input": "bagaimana cuaca besok",
        "description": "Weather forecast question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "weather tomorrow",
        "description": "Weather forecast question - English normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "ramalan cuaca",
        "description": "Weather forecast question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "cuaca di jakarta",
        "description": "Weather location question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "amerika serikat",
        "description": "Non-Indonesia location - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "jepang bagaimana",
        "description": "Non-Indonesia location question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "thailand aman tidak",
        "description": "Non-Indonesia safety question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "petir menyambar",
        "description": "Non-geological hazard - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "tornado terjadi",
        "description": "Non-geological hazard - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "banjir jakarta",
        "description": "Non-geological disaster - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "politik indonesia",
        "description": "Politics question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "ekonomi bagaimana",
        "description": "Economics question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "olahraga sepak bola",
        "description": "Sports question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "hiburan musik",
        "description": "Entertainment question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "kesehatan jantung",
        "description": "Health question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "covid 19",
        "description": "Health pandemic question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "makanan enak",
        "description": "Food question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "teknologi komputer",
        "description": "Technology question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "sejarah indonesia",
        "description": "History question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "matematika sulit",
        "description": "Mathematics question - normal",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    
    # Category 10: Mixed/Complex Cases - NORMAL VERSIONS ONLY
    {
        "input": "halo, status gunung merapi bagaimana",
        "description": "Greeting + technical question - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "terima kasih atas informasi tentang gunung",
        "description": "Thanks + geological context - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "kamu bisa bantu cek gempa sekarang tidak",
        "description": "Capability + technical mix - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "hai, siapa kamu dan apa yang bisa kamu lakukan",
        "description": "Greeting + identity + capability - normal",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "terima kasih atas bantuan dengan informasi gunung",
        "description": "Thanks + geological help - normal",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    
    # Category 11: Edge Cases - NORMAL VERSIONS ONLY
    {
        "input": "gunung",
        "description": "Single geological keyword - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gempa",
        "description": "Single word earthquake - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "volcano",
        "description": "Single English keyword - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "earthquake",
        "description": "Single English keyword - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "halo 123",
        "description": "Greeting with numbers - normal",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "status 123",
        "description": "Keyword with numbers - normal",
        "expected_intent": "technical",
        "geo_location": None
    },
    # Category 1: Greetings (with typos)
    {
        "input": "haloo",
        "description": "Greeting with extra letter typo",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "selamat pgi",
        "description": "Greeting with missing letter typo",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "haii apakbar",
        "description": "Combined greeting with typos",
        "expected_intent": "greeting",
        "geo_location": None
    },
    {
        "input": "good morningg",
        "description": "English greeting with typo",
        "expected_intent": "greeting",
        "geo_location": None
    },
    
    # Category 2: Identity Questions (with typos)
    {
        "input": "siapakamuu",
        "description": "Identity question with typo",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "kamu siappaa",
        "description": "Identity question with repeated letter typo",
        "expected_intent": "identity",
        "geo_location": None
    },
    {
        "input": "who aree you",
        "description": "English identity with typo",
        "expected_intent": "identity",
        "geo_location": None
    },
    
    # Category 3: Capability Questions (with typos)
    {
        "input": "apaa yg bisa kamu lakuin",
        "description": "Capability question with typos",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "km bsa apa",
        "description": "Shortened capability question with typos",
        "expected_intent": "capability",
        "geo_location": None
    },
    {
        "input": "fungsikmu apaa",
        "description": "Function question with typos",
        "expected_intent": "capability",
        "geo_location": None
    },
    
    # Category 4: Location-Required Questions (WITHOUT location)
    {
        "input": "apakah saya aman",
        "description": "Safety question without location provided",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "daerah saya bahaya tidak",
        "description": "Area safety question without location",
        "expected_intent": "location_required",
        "geo_location": None
    },
    {
        "input": "apakah aku dlm bahaya",
        "description": "Danger question with abbreviation typo",
        "expected_intent": "location_required",
        "geo_location": None
    },
    
    # Category 5: Location-Required Questions (WITH location)
    {
        "input": "apakah saya aman",
        "description": "Safety question WITH valid GPS location",
        "expected_intent": "technical",  # Should become technical since location is provided
        "geo_location": (-7.7956, 110.3695)  # Yogyakarta coordinates
    },
    {
        "input": "daerah saya rawan bencana",
        "description": "Disaster-prone question WITH location",
        "expected_intent": "technical",  # Should become technical
        "geo_location": (-6.2088, 106.8456)  # Jakarta coordinates
    },
    {
        "input": "apkh wilaya sy aman",
        "description": "Typo-filled safety question WITH location",
        "expected_intent": "technical",  # Should become technical
        "geo_location": (-7.2504, 112.7688)  # Surabaya coordinates
    },
    
    # Category 6: Technical Geological Questions
    {
        "input": "status gunung merapi",
        "description": "Standard volcano status question",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "sttus gunung merapi skrg",
        "description": "Volcano status with typos and slang",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gempabumi hari ini",
        "description": "Earthquake query",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "gempa skrg",
        "description": "Short earthquake query with typo",
        "expected_intent": "technical",
        "geo_location": None
    },
    {
        "input": "aktivitas gunung semeruu",
        "description": "Volcano activity with typo",
        "expected_intent": "technical",
        "geo_location": None
    },
    
    # Category 7: Count/List Questions
    {
        "input": "ada brp gunung api",
        "description": "Count question with typos",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "berapa bnyk gunung aktif",
        "description": "How many volcanoes question",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    {
        "input": "daftar gunung api",
        "description": "List volcanoes question",
        "expected_intent": "count_list_query",
        "geo_location": None
    },
    
    # Category 8: General Chat
    {
        "input": "terimakasih yaa",
        "description": "Thank you with typos",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "makasih bngt",
        "description": "Thanks with slang and typo",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "apakabar",
        "description": "How are you without space",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    {
        "input": "bagusss bangett",
        "description": "Praise with repeated letters",
        "expected_intent": "general_chat",
        "geo_location": None
    },
    
    # Category 9: Out of Scope Questions
    {
        "input": "cuaca besok gimana",
        "description": "Weather forecast question",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "ramlan cuaca jkt",
        "description": "Weather forecast with typos",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "politik indonesia skrg",
        "description": "Politics question",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "olahraga bola",
        "description": "Sports question",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "ekonomi indonesia",
        "description": "Economics question",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    
    # Category 10: Mixed/Complex Cases
    {
        "input": "halo, status gunung merapi bagaimana?",
        "description": "Greeting + technical question",
        "expected_intent": "technical",  # Should prioritize technical
        "geo_location": None
    },
    {
        "input": "makasih atas infonya ttg gunung",
        "description": "Thanks + geological context",
        "expected_intent": "general_chat",  # Should still be general chat
        "geo_location": None
    },
    {
        "input": "kamu bisa bantu cek gempa skrg gak?",
        "description": "Capability + technical mix",
        "expected_intent": "technical",  # Has technical keyword
        "geo_location": None
    },
    
    # Category 11: Edge Cases
    {
        "input": "a",
        "description": "Single character input",
        "expected_intent": "out_of_scope",  # Too short, likely OOS
        "geo_location": None
    },
    {
        "input": "",
        "description": "Empty input",
        "expected_intent": "greeting",  # Fallback
        "geo_location": None
    },
    {
        "input": "123456",
        "description": "Numbers only",
        "expected_intent": "out_of_scope",
        "geo_location": None
    },
    {
        "input": "gunung",
        "description": "Single geological keyword",
        "expected_intent": "technical",
        "geo_location": None
    },
]

# ======================================================
# Test Runner
# ======================================================
import json
import csv
from datetime import datetime
import os

def run_inference_tests():
    """Run comprehensive inference tests on the trained model and save to logs"""
    
    # Create logs directory if it doesn't exist
    INFERENCE_LOGS_DIR = "inference_logs"
    os.makedirs(INFERENCE_LOGS_DIR, exist_ok=True)
    
    # Create timestamp for this inference run
    inference_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_prefix = f"inference_{inference_timestamp}"
    
    print("🔍 Loading MAGMA Intent Classifier...")
    try:
        classifier = MAGMAIntentClassifier()
        print("✅ Model loaded successfully!")
        print(f"📊 Model has {len(classifier.encoder.classes_)} intents:")
        for intent in classifier.encoder.classes_:
            print(f"  - {intent}")
        print()
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return
    
    print("🧪 Running Inference Tests...")
    print("=" * 80)
    
    results = []
    category_counts = {}
    errors = []
    
    # Open detailed log file
    detailed_log_path = os.path.join(INFERENCE_LOGS_DIR, f"{log_prefix}_detailed.log")
    with open(detailed_log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"MAGMA Intent Model Inference Test - {inference_timestamp}\n")
        log_file.write("=" * 80 + "\n\n")
        
        for i, test in enumerate(test_cases, 1):
            user_input = test["input"]
            description = test["description"]
            expected = test["expected_intent"]
            geo_location = test["geo_location"]
            
            # Skip empty input case
            if user_input == "":
                continue
                
            # Write to console and log file
            test_header = f"\nTest {i:3d}: {description}"
            print(test_header)
            log_file.write(test_header + "\n")
            
            input_info = f"       Input: '{user_input}'"
            print(input_info)
            log_file.write(input_info + "\n")
            
            if geo_location:
                loc_info = f"       Location: {geo_location}"
                print(loc_info)
                log_file.write(loc_info + "\n")
            
            try:
                # Get prediction
                result = classifier.predict(user_input, geo_location)
                
                predicted = result["intent"]
                confidence = result["confidence"]
                cleaned = result["cleaned_text"]
                
                # Check if correct
                is_correct = predicted == expected
                status = "✅" if is_correct else "❌"
                
                # Prepare output lines
                output_lines = [
                    f"       Cleaned: '{cleaned}'",
                    f"       Predicted: {predicted} (confidence: {confidence:.3f})",
                    f"       Expected: {expected}",
                    f"       Result: {status} {'CORRECT' if is_correct else 'WRONG'}",
                    f"       Requires API: {result['requires_api']}"
                ]
                
                # Print and log
                for line in output_lines:
                    print(line)
                    log_file.write(line + "\n")
                
                # Track category
                category = description.split(":")[0] if ":" in description else "Other"
                category_counts[category] = category_counts.get(category, 0) + 1
                
                # Store result
                result_entry = {
                    "test_id": i,
                    "input": user_input,
                    "cleaned": cleaned,
                    "predicted": predicted,
                    "expected": expected,
                    "confidence": float(confidence),
                    "correct": is_correct,
                    "geo_location": geo_location,
                    "description": description,
                    "requires_api": result["requires_api"],
                    "all_probabilities": result.get("all_probabilities", {})
                }
                results.append(result_entry)
                
            except Exception as e:
                error_msg = f"       ❌ Error: {e}"
                print(error_msg)
                log_file.write(error_msg + "\n")
                
                errors.append({
                    "test_id": i,
                    "input": user_input,
                    "description": description,
                    "error": str(e)
                })
        
        log_file.write("\n" + "=" * 80 + "\n")
        log_file.write("END OF INFERENCE TEST\n")
    
    print(f"\n💾 Detailed test log saved to: {detailed_log_path}")
    
    # ======================================================
    # Save Results to JSON
    # ======================================================
    json_results = {
        "metadata": {
            "timestamp": inference_timestamp,
            "total_tests": len(results) + len(errors),
            "successful_tests": len(results),
            "failed_tests": len(errors),
            "model_intents": classifier.encoder.classes_.tolist(),
            "model_description": "MAGMA Intent Classification Model"
        },
        "summary": {
            "total_correct": sum(1 for r in results if r["correct"]),
            "total_incorrect": sum(1 for r in results if not r["correct"]),
            "accuracy": (sum(1 for r in results if r["correct"]) / len(results) * 100) if results else 0
        },
        "category_stats": category_counts,
        "detailed_results": results,
        "errors": errors
    }
    
    json_path = os.path.join(INFERENCE_LOGS_DIR, f"{log_prefix}_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON results saved to: {json_path}")
    
    # ======================================================
    # Save Results to CSV
    # ======================================================
    csv_path = os.path.join(INFERENCE_LOGS_DIR, f"{log_prefix}_results.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'test_id', 'input', 'cleaned', 'predicted', 'expected', 
            'confidence', 'correct', 'requires_api', 'description',
            'has_location'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow({
                'test_id': result['test_id'],
                'input': result['input'],
                'cleaned': result['cleaned'],
                'predicted': result['predicted'],
                'expected': result['expected'],
                'confidence': f"{result['confidence']:.3f}",
                'correct': 'YES' if result['correct'] else 'NO',
                'requires_api': 'YES' if result['requires_api'] else 'NO',
                'description': result['description'],
                'has_location': 'YES' if result['geo_location'] else 'NO'
            })
    print(f"💾 CSV results saved to: {csv_path}")
    
    # ======================================================
    # Generate Summary Report
    # ======================================================
    summary_path = os.path.join(INFERENCE_LOGS_DIR, f"{log_prefix}_summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as summary_file:
        summary_file.write(f"MAGMA Intent Model Inference Summary\n")
        summary_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        summary_file.write("=" * 60 + "\n\n")
        
        # Overall statistics
        total_correct = sum(1 for r in results if r["correct"])
        total_tests = len(results)
        accuracy = (total_correct / total_tests * 100) if total_tests > 0 else 0
        
        summary_file.write(f"📊 OVERALL STATISTICS:\n")
        summary_file.write(f"  Total Tests: {total_tests}\n")
        summary_file.write(f"  Correct Predictions: {total_correct}\n")
        summary_file.write(f"  Incorrect Predictions: {total_tests - total_correct}\n")
        summary_file.write(f"  Accuracy: {accuracy:.1f}%\n")
        summary_file.write(f"  Errors: {len(errors)}\n\n")
        
        # Per-intent statistics
        summary_file.write(f"🎯 PER-INTENT ACCURACY:\n")
        intent_stats = {}
        for result in results:
            intent = result["predicted"]
            if intent not in intent_stats:
                intent_stats[intent] = {"total": 0, "correct": 0}
            intent_stats[intent]["total"] += 1
            if result["correct"]:
                intent_stats[intent]["correct"] += 1
        
        for intent, stats in sorted(intent_stats.items()):
            intent_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            summary_file.write(f"  {intent:20s}: {intent_acc:5.1f}% ({stats['correct']:3d}/{stats['total']:3d})\n")
        
        summary_file.write(f"\n📍 LOCATION-AWARE STATISTICS:\n")
        location_tests = [r for r in results if r["geo_location"]]
        non_location_tests = [r for r in results if not r["geo_location"]]
        
        if location_tests:
            location_correct = sum(1 for r in location_tests if r["correct"])
            location_acc = (location_correct / len(location_tests) * 100) if location_tests else 0
            summary_file.write(f"  With Location: {len(location_tests)} tests, {location_acc:.1f}% accuracy\n")
        
        if non_location_tests:
            non_location_correct = sum(1 for r in non_location_tests if r["correct"])
            non_location_acc = (non_location_correct / len(non_location_tests) * 100) if non_location_tests else 0
            summary_file.write(f"  Without Location: {len(non_location_tests)} tests, {non_location_acc:.1f}% accuracy\n")
        
        # Confidence distribution
        summary_file.write(f"\n📈 CONFIDENCE DISTRIBUTION:\n")
        confidence_ranges = {
            "0.9-1.0": 0,
            "0.8-0.9": 0,
            "0.7-0.8": 0,
            "0.6-0.7": 0,
            "0.5-0.6": 0,
            "<0.5": 0
        }
        
        for result in results:
            conf = result["confidence"]
            if conf >= 0.9:
                confidence_ranges["0.9-1.0"] += 1
            elif conf >= 0.8:
                confidence_ranges["0.8-0.9"] += 1
            elif conf >= 0.7:
                confidence_ranges["0.7-0.8"] += 1
            elif conf >= 0.6:
                confidence_ranges["0.6-0.7"] += 1
            elif conf >= 0.5:
                confidence_ranges["0.5-0.6"] += 1
            else:
                confidence_ranges["<0.5"] += 1
        
        for range_name, count in confidence_ranges.items():
            percentage = (count / total_tests * 100) if total_tests > 0 else 0
            summary_file.write(f"  {range_name:10s}: {count:3d} tests ({percentage:5.1f}%)\n")
        
        # Incorrect predictions
        incorrect = [r for r in results if not r["correct"]]
        if incorrect:
            summary_file.write(f"\n❌ INCORRECT PREDICTIONS ({len(incorrect)}):\n")
            for result in incorrect[:10]:  # Show first 10
                summary_file.write(f"  Test {result['test_id']:3d}: '{result['input'][:30]}...'\n")
                summary_file.write(f"       Expected: {result['expected']}, Predicted: {result['predicted']} (conf: {result['confidence']:.3f})\n")
        
        # Errors
        if errors:
            summary_file.write(f"\n⚠️  ERRORS ({len(errors)}):\n")
            for error in errors:
                summary_file.write(f"  Test {error['test_id']:3d}: {error['description']}\n")
                summary_file.write(f"       Error: {error['error']}\n")
    
    print(f"💾 Summary report saved to: {summary_path}")
    
    # ======================================================
    # Print Summary to Console
    # ======================================================
    print("\n" + "=" * 80)
    print("📊 INFERENCE TEST SUMMARY")
    print("=" * 80)
    
    total_correct = sum(1 for r in results if r["correct"])
    total_tests = len(results)
    accuracy = (total_correct / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n✅ Overall Accuracy: {accuracy:.1f}% ({total_correct}/{total_tests})")
    
    # Quick intent accuracy
    print(f"\n🎯 Top Performing Intents:")
    intent_accuracies = []
    for intent, stats in intent_stats.items():
        intent_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        intent_accuracies.append((intent, intent_acc, stats["correct"], stats["total"]))
    
    # Sort by accuracy (descending)
    intent_accuracies.sort(key=lambda x: x[1], reverse=True)
    for intent, acc, correct, total in intent_accuracies[:5]:
        print(f"  {intent:20s}: {acc:5.1f}% ({correct:2d}/{total:2d})")
    
    # Worst performing
    print(f"\n⚠️  Lowest Performing Intents:")
    for intent, acc, correct, total in intent_accuracies[-3:]:
        print(f"  {intent:20s}: {acc:5.1f}% ({correct:2d}/{total:2d})")
    
    # Location impact
    if location_tests:
        location_acc = (sum(1 for r in location_tests if r["correct"]) / len(location_tests) * 100) if location_tests else 0
        print(f"\n📍 Location Impact:")
        print(f"  Tests with location: {len(location_tests)}")
        print(f"  Accuracy with location: {location_acc:.1f}%")
    
    # Confidence stats
    high_conf = sum(1 for r in results if r["confidence"] >= 0.8)
    high_conf_percentage = (high_conf / total_tests * 100) if total_tests > 0 else 0
    print(f"\n📈 Confidence Statistics:")
    print(f"  High confidence (≥0.8): {high_conf} tests ({high_conf_percentage:.1f}%)")
    
    # File locations
    print(f"\n💾 Log Files Created:")
    print(f"  ├── {detailed_log_path}")
    print(f"  ├── {json_path}")
    print(f"  ├── {csv_path}")
    print(f"  └── {summary_path}")
    
    print("\n" + "=" * 80)
    print("✅ Inference Testing Complete!")
    print("=" * 80)
    
    return {
        "accuracy": accuracy,
        "total_tests": total_tests,
        "correct_tests": total_correct,
        "log_files": {
            "detailed_log": detailed_log_path,
            "json_results": json_path,
            "csv_results": csv_path,
            "summary": summary_path
        }
    }

# ======================================================
# Interactive Inference Demo
# ======================================================
def interactive_demo():
    """Interactive demo for testing custom inputs"""
    
    print("\n" + "=" * 80)
    print("🎮 INTERACTIVE INFERENCE DEMO")
    print("=" * 80)
    print("\nType 'quit' to exit, 'help' for commands\n")
    
    classifier = MAGMAIntentClassifier()
    
    while True:
        try:
            user_input = input("\n💬 Enter your query: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'help':
                print("\n📋 Available commands:")
                print("  quit                    - Exit the demo")
                print("  help                    - Show this help")
                print("  location                - Set location for next query")
                print("  clear                   - Clear location")
                print("  show                    - Show current location")
                print("  stats                   - Show intent probabilities")
                print("  Any text                - Classify the intent")
                continue
            elif user_input.lower() == 'location':
                try:
                    lat = float(input("Enter latitude (e.g., -7.7956): "))
                    lon = float(input("Enter longitude (e.g., 110.3695): "))
                    global current_location
                    current_location = (lat, lon)
                    print(f"📍 Location set to: {current_location}")
                except ValueError:
                    print("❌ Invalid coordinates")
                continue
            elif user_input.lower() == 'clear':
                current_location = None
                print("📍 Location cleared")
                continue
            elif user_input.lower() == 'show':
                if 'current_location' in globals() and current_location:
                    print(f"📍 Current location: {current_location}")
                else:
                    print("📍 No location set")
                continue
            elif user_input.lower() == 'stats':
                # Show sample statistics
                sample_text = input("Enter text to see probabilities: ")
                result = classifier.predict(sample_text)
                print(f"\n📊 Probabilities for '{sample_text}':")
                for intent, prob in sorted(result.get("all_probabilities", {}).items(), 
                                         key=lambda x: x[1], reverse=True):
                    print(f"  {intent:20s}: {prob:.4f}")
                continue
            
            # Get prediction
            location = current_location if 'current_location' in globals() else None
            result = classifier.predict(user_input, location)
            
            # Display results
            print("\n" + "─" * 40)
            print(f"📝 Query: {user_input}")
            print(f"🧹 Cleaned: {result['cleaned_text']}")
            if location:
                print(f"📍 Location: {location}")
            print(f"🎯 Intent: {result['intent']}")
            print(f"📊 Confidence: {result['confidence']:.3f}")
            print(f"🔧 Requires API: {result['requires_api']}")
            print(f"Output: {get_intent_response(result['intent'], user_input)}")
            
            # Show top 3 probabilities
            print("\n📈 Top predictions:")
            probs = result.get("all_probabilities", {})
            sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
            for intent, prob in sorted_probs:
                print(f"  {intent:20s}: {prob:.4f}")
            print("─" * 40)
            
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

# ======================================================
# Location-Aware Case Study
# ======================================================
def location_aware_case_study():
    """Demonstrate the difference location makes in predictions"""
    
    print("\n" + "=" * 80)
    print("📍 LOCATION-AWARE CASE STUDY")
    print("=" * 80)
    
    classifier = MAGMAIntentClassifier()
    
    # Common safety questions
    safety_queries = [
        "apakah saya aman",
        "daerah saya bahaya tidak",
        "apakah lokasi saya rawan bencana",
        "am i safe",
    ]
    
    # Different locations in Indonesia
    locations = {
        "Yogyakarta (near Merapi)": (-7.540, 110.446),
        "Jakarta (urban)": (-6.2088, 106.8456),
        "Bali (tourist area)": (-8.4095, 115.1889),
        "Bandung (mountainous)": (-6.9175, 107.6191),
        None: None  # No location
    }
    
    results_table = []
    
    for query in safety_queries:
        row = {"Query": query}
        for location_name, coords in locations.items():
            result = classifier.predict(query, coords)
            row[location_name] = {
                "intent": result["intent"],
                "requires_api": result["requires_api"],
                "confidence": f"{result['confidence']:.3f}"
            }
        results_table.append(row)
    
    # Display results
    print("\n🔍 Impact of Location on Intent Classification:\n")
    
    # Header
    headers = ["Query"] + list(locations.keys())
    print(f"{'Query':30s}", end="")
    for loc in locations.keys():
        print(f"{str(loc)[:15]:15s}", end="")
    print()
    print("-" * 100)
    
    # Rows
    for row in results_table:
        print(f"{row['Query'][:30]:30s}", end="")
        for loc in locations.keys():
            if loc in row:
                intent_char = "T" if row[loc]["intent"] == "technical" else "L"
                print(f"{intent_char}({row[loc]['confidence']}):{row[loc]['requires_api']!s:5s}", end="")
        print()
    
    print("\nLegend: T = technical, L = location_required")
    print("       Requires API: True/False")
    
    print("\n📌 Key Insights:")
    print("1. Same query 'apakah saya aman' without location → 'location_required'")
    print("2. Same query with location → 'technical' (goes to API)")
    print("3. This reduces unnecessary prompts for location")
    print("4. API calls only made when location is available")

# ======================================================
# Typo Resilience Test
# ======================================================
def typo_resilience_test():
    """Test how well the model handles various typos"""
    
    print("\n" + "=" * 80)
    print("✏️  TYPO RESILIENCE TEST")
    print("=" * 80)
    
    classifier = MAGMAIntentClassifier()
    
    # Base queries and their expected intents
    base_queries = [
        ("halo", "greeting"),
        ("siapa kamu", "identity"),
        ("apa yang bisa kamu lakukan", "capability"),
        ("status gunung merapi", "technical"),
        ("terima kasih", "general_chat"),
    ]
    
    # Typo variations
    typo_patterns = [
        ("Extra letters", lambda s: s + s[-1]),  # Double last letter
        ("Missing vowels", lambda s: s.replace('a', '').replace('i', '').replace('u', '').replace('e', '').replace('o', '')),
        ("Swapped letters", lambda s: s[:-2] + s[-1] + s[-2] if len(s) > 2 else s),
        ("Missing spaces", lambda s: s.replace(' ', '')),
        ("All caps", lambda s: s.upper()),
        ("Random case", lambda s: ''.join(c.upper() if i % 3 == 0 else c for i, c in enumerate(s))),
    ]
    
    results = []
    
    for base_query, expected_intent in base_queries:
        print(f"\n🔤 Base query: '{base_query}' (expected: {expected_intent})")
        
        for typo_name, typo_func in typo_patterns:
            try:
                typo_query = typo_func(base_query)
                result = classifier.predict(typo_query)
                
                is_correct = result["intent"] == expected_intent
                status = "✅" if is_correct else "❌"
                
                print(f"  {typo_name:15s}: '{typo_query:20s}' → {result['intent']:15s} {status} ({result['confidence']:.3f})")
                
                results.append({
                    "base": base_query,
                    "typo_type": typo_name,
                    "typo_query": typo_query,
                    "predicted": result["intent"],
                    "expected": expected_intent,
                    "correct": is_correct,
                    "confidence": result["confidence"]
                })
                
            except Exception as e:
                print(f"  {typo_name:15s}: ERROR - {e}")
    
    # Calculate typo resilience score
    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    resilience_score = (correct_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n📊 Typo Resilience Score: {resilience_score:.1f}% ({correct_count}/{total_count})")
    
    # Per-intent typo resilience
    print(f"\n🎯 Per-Intent Typo Resilience:")
    intent_stats = {}
    for result in results:
        intent = result["expected"]
        if intent not in intent_stats:
            intent_stats[intent] = {"total": 0, "correct": 0}
        intent_stats[intent]["total"] += 1
        if result["correct"]:
            intent_stats[intent]["correct"] += 1
    
    for intent, stats in sorted(intent_stats.items()):
        score = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {intent:20s}: {score:5.1f}% ({stats['correct']:2d}/{stats['total']:2d})")


def test_case_inference():
    """Run inference tests on predefined test cases and log results"""
    print("🔍 Loading MAGMA Intent Classifier...")
    try:
        classifier = MAGMAIntentClassifier()
        print("✅ Model loaded successfully!")
        print(f"📊 Model has {len(classifier.encoder.classes_)} intents:")
        for intent in classifier.encoder.classes_:
            print(f"  - {intent}")
        print()
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    # Initialize counters and fail list
    total_count = len(esdm_test)
    correct_count = 0
    incorrect_count = 0
    failed_samples = []

    for test in esdm_test:
        user_input = test["input"]
        expected = test["expected_intent"]
        geo_location = test["geo_location"]

        # Run prediction
        result = classifier.predict(user_input, geo_location)
        
        predicted = result["intent"]
        confidence = result["confidence"]
        cleaned = result["cleaned_text"]
        
        # Check if correct
        is_correct = (predicted == expected)
        
        if is_correct:
            correct_count += 1
            status = "✅"
        else:
            incorrect_count += 1
            status = "❌"
            # Store the details for the report
            failed_samples.append({
                "input": user_input,
                "predicted": predicted,
                "expected": expected
            })
        
        generated_response = get_intent_response(predicted, user_input)
    
        # Prepare output lines
        output_lines = [
            f"\nInput: '{user_input}'",
            f"       Cleaned: '{cleaned}'",
            f"       Predicted: {predicted} (confidence: {confidence:.4f})",
            f"       Expected: {expected}",
            f"       Result: {status} {'CORRECT' if is_correct else 'WRONG'}",
            f"       Requires API: {result['requires_api']}",
            f"       Response: \"{generated_response}\"" # Added this line
        ]
        
        # Print results for this case
        for line in output_lines:
            print(line)

    # --- FINAL REPORT SECTION ---
    accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
    
    print("\n" + "="*50)
    print("📊 FINAL INFERENCE REPORT")
    print("="*50)
    print(f"Total Tests:  {total_count}")
    print(f"Correct:      {correct_count}")
    print(f"Incorrect:    {incorrect_count}")
    print(f"Accuracy:     {accuracy:.2f}%")
    print("-"*50)

    if failed_samples:
        print("\n❌ LIST OF INCORRECT SAMPLES:")
        for i, sample in enumerate(failed_samples, 1):
            print(f"{i}. Input: \"{sample['input']}\"")
            print(f"   Predicted: {sample['predicted']} | Expected: {sample['expected']}")
            print("-" * 30)
    else:
        print("\n🎉 PERFECT SCORE! All predictions matched the expected intents.")
    
    print("="*50)

# ======================================================
# Main Execution
# ======================================================
if __name__ == "__main__":
    print("🚀 MAGMA Intent Model Inference Tests")
    print("=" * 80)
    
    # Run all tests
    # run_inference_tests()
    
    # # Run specialized tests
    # location_aware_case_study()
    
    # typo_resilience_test()
    
    # Start interactive demo
    interactive_demo()

    # Run test case inference
    # test_case_inference()