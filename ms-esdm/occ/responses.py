from typing import Optional

MAGMA_PERSONA = {
    "name": "MAGMA Indonesia",
    "full_name": "Multiplatform Application for Geohazard Mitigation and Assessment",
    "organization": "PVMBG (Pusat Vulkanologi dan Mitigasi Bencana Geologi)",
    "parent": "Badan Geologi, Kementerian ESDM Republik Indonesia",
    "role": "Asisten virtual untuk informasi mitigasi bencana geologi",
    "description": "MAGMA Indonesia (Multiplatform Application for Geohazard Mitigation and Assessment in Indonesia) adalah aplikasi multiplatform (web & mobile) dalam jaringan berisikan informasi dan rekomendasi kebencanaan geologi terintegrasi (gunungapi, gempabumi, tsunami, dan gerakan tanah) yang disajikan kepada masyarakat secara kuasi-realtime dan interaktif. Sistem ini dibangun dan dikembangkan secara mandiri oleh PNS Pusat Vulkanologi dan Mitigasi Bencana Geologi (PVMBG) sejak tahun 2015 dengan menggunakan teknologi terkini berbasis open-source. MAGMA Indonesia meliputi aplikasi yang digunakan secara internal/pegawai (analisis data dan pelaporan) maupun eksternal/publik (informasi dan rekomendasi). Prinsip utama MAGMA Indonesia adalah mengubah data menjadi informasi dan rekomendasi yang mudah dipahami oleh masyarakat umum. MAGMA Indonesia adalah sistem yang terus belajar dan berevolusi, fitur-fitur baru akan lahir disesuaikan dengan kebutuhan jaman.",
    "capabilities": [
        "Informasi aktivitas gunung api real-time",
        "Status dan peringatan gunung api (VAR, VEN, VONA)",
        "Data gempabumi terkini",
        "Informasi bahaya gerakan tanah",
        "Rekomendasi keselamatan berdasarkan lokasi"
    ]
}

class ResponseTemplates:
    """Pre-defined responses for common questions"""
    
    @staticmethod
    def get_greeting_response() -> str:
        return (
            f"Halo! Saya {MAGMA_PERSONA['name']} ({MAGMA_PERSONA['full_name']}), "
            f"asisten virtual dari {MAGMA_PERSONA['organization']}, {MAGMA_PERSONA['parent']}. "
            f"\n\n{MAGMA_PERSONA['description']}\n\n"
            f"Saya siap membantu Anda dengan informasi seputar bahaya geologi seperti aktivitas gunung api, "
            f"gempabumi, tsunami, dan gerakan tanah. Ada yang bisa saya bantu?"
        )
    
    @staticmethod
    def get_identity_response() -> str:
        return (
            f"Saya adalah {MAGMA_PERSONA['name']} ({MAGMA_PERSONA['full_name']}), "
            f"asisten virtual mitigasi bencana geologi dari {MAGMA_PERSONA['organization']}, "
            f"yang merupakan bagian dari {MAGMA_PERSONA['parent']}.\n\n"
            f"Saya dirancang untuk membantu masyarakat memahami kondisi kebencanaan geologi di Indonesia "
            f"dengan menyediakan informasi terkini yang bersumber dari data resmi PVMBG."
        )
    
    @staticmethod
    def get_capability_response() -> str:
        caps = "\n".join([f"• {cap}" for cap in MAGMA_PERSONA['capabilities']])
        return (
            f"Saya dapat membantu Anda dengan:\n\n{caps}\n\n"
            f"Anda dapat bertanya tentang status gunung api tertentu, kondisi kebencanaan di wilayah Anda, "
            f"atau meminta penjelasan tentang data geologis."
        )
    
    @staticmethod
    def get_general_chat_response(user_input: str) -> Optional[str]:
        text_lower = user_input.lower()
        if any(word in text_lower for word in ['apa kabar', 'how are you']):
            return "Saya baik-baik saja, terima kasih! Saya siap membantu Anda. Ada yang bisa saya bantu hari ini?"
        if any(word in text_lower for word in ['terima kasih', 'thank you', 'thanks']):
            return "Sama-sama! Senang bisa membantu. Jika ada pertanyaan lain, jangan ragu untuk bertanya."
        if any(word in text_lower for word in ['bagus', 'mantap', 'keren', 'nice', 'great']):
            return "Terima kasih! Saya senang bisa memberikan pelayanan terbaik."
        return None
    
    @staticmethod
    def get_clarification_response(user_input: str) -> str:
        return (
            f"Maaf, saya kurang memahami pertanyaan Anda: \"{user_input}\". "
            f"Bisakah Anda memperjelas? Misalnya: \"Bagaimana kondisi Gunung Merapi?\""
        )

    @staticmethod
    def get_landslide_response() -> str:
        return (
            f"Terima kasih atas pertanyaan tentang gerakan tanah/tanah longsor. "
            f"Saat ini sistem saya fokus pada pemantauan gunung api. Untuk info gerakan tanah, "
            f"silakan cek https://magma.esdm.go.id."
        )
    
    @staticmethod
    def get_count_list_response() -> str:
        return (
            f"Indonesia memiliki **127 gunung api aktif**. Beberapa yang paling dikenal antara lain: "
            f"Merapi, Semeru, Sinabung, Agung, dan Krakatau."
        )
    
    @staticmethod
    def get_out_of_scope_response() -> str:
        return (
            f"Mohon maaf, keahlian saya terbatas pada informasi kebencanaan geologi di Indonesia. "
            f"Silakan tanyakan hal-hal terkait gunung api, gempa, atau tsunami!"
        )
    
    @staticmethod
    def get_location_required_response() -> str:
        return (
            f"Untuk menjawab pertanyaan tersebut, saya memerlukan informasi lokasi. "
            f"Mohon aktifkan lokasi di device anda atau sebutkan nama daerah Anda, misalnya: \"Apakah daerah Yogyakarta aman?\""
        )

    @staticmethod
    def get_status_response() -> str:
        return (
            "Status gunungapi ada 4 level, yaitu:\n\n"
            "Level I (Normal): Tidak ada indikasi peningkatan aktivitas vulkanik baik secara visual maupun kegempaan.\n"
            "Level II (Waspada): Peningkatan aktivitas vulkanik bisa diamati secara jelas baik visual maupun kegempaan. "
            "Ancaman letusan melingkupi area Kawasan Rawan Bencana (KRB) III.\n"
            "Level III (Siaga): Terjadi peningkatan aktivitas vulkanik secara signifikan. "
            "Letusan kemungkinan besar terjadi dan area potensi bahaya letusan berada di daerah Kawasan Rawan Bencana (KRB) II.\n"
            "Level IV (Awas): Memiliki potensi besar terjadi letusan gunungapi. Diperlukan evakuasi penduduk."
        )

def get_intent_response(intent: str, user_input: str) -> str:
    """Utility function to map intent to a template"""
    templates = ResponseTemplates()
    
    mapping = {
        'greeting': templates.get_greeting_response,
        'identity': templates.get_identity_response,
        'capability': templates.get_capability_response,
        'location_required': templates.get_location_required_response,
        'out_of_scope': templates.get_out_of_scope_response,
        'count_list_query': templates.get_count_list_response,
        'status': templates.get_status_response,
        'technical': lambda: "Sedang memproses data teknis geologi..."
    }

    if intent == 'general_chat':
        chat_resp = templates.get_general_chat_response(user_input)
        return chat_resp if chat_resp else "Saya mengerti, ada lagi yang bisa saya bantu?"
    
    # Get from mapping or fallback to clarification
    response_func = mapping.get(intent, lambda: templates.get_clarification_response(user_input))
    
    # Check if we need to call with arguments or not
    try:
        return response_func()
    except TypeError:
        return response_func(user_input)