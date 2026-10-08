import asyncio

from services import whatsapp_follow_ups as follow_ups
from services.whatsapp_volcano_region import (
    named_volcano_answer,
    ranked_volcano_answer,
    regional_volcano_answer,
)


def test_region_is_not_treated_as_volcano(monkeypatch):
    monkeypatch.setattr(follow_ups, "load_volcano_cache", lambda: [])
    assert follow_ups._known_volcano_from_question("Daftar gunung api Jawa Barat") is None
    assert follow_ups._known_volcano_from_question("Status Gunung Ibu") == "Ibu"
    assert all(
        "Gunung Jawa Barat" not in item["question"]
        for item in follow_ups._api_candidates("Daftar gunung api Jawa Barat", "Status gunung api")
    )


def test_offer_uses_nara_voice_without_system_label():
    offer = follow_ups.format_nara_follow_up(
        "Apa rekomendasi resmi PVMBG untuk Gunung Ibu?"
    )
    assert "Apakah Anda ingin tahu rekomendasi resmi PVMBG untuk Gunung Ibu?" in offer
    assert "NARA" in offer
    assert "Pertanyaan lanjutan" not in offer


def test_no_follow_up_for_scope_mismatch_or_missing_result():
    async def generate(question, answer):
        return await follow_ups.DynamicFollowUpGenerator.generate(
            mode="api", question=question, answer=answer,
            references=[], previous=[], model=None,
        )

    assert asyncio.run(generate(
        "Daftar gunung api Jawa Barat",
        "Berikut adalah status aktivitas seluruh gunung api di Indonesia saat ini.",
    )) is None
    assert asyncio.run(generate(
        "Status Gunung Jawa Barat Saat",
        "Gunung Jawa Barat Saat tidak ditemukan. Silakan periksa kembali ejaan nama gunung.",
    )) is None


def test_whatsapp_volcano_list_is_filtered_to_requested_province():
    volcanoes = [
        {"ga_nama_gapi": "Ciremai", "ga_prov_gapi": "Jawa Barat", "ga_status": 1},
        {"ga_nama_gapi": "Gede", "ga_prov_gapi": "Jawa Barat", "ga_status": 2},
        {"ga_nama_gapi": "Semeru", "ga_prov_gapi": "Jawa Timur", "ga_status": 3},
        {"ga_nama_gapi": "Merapi", "ga_prov_gapi": "Daerah Istimewa Yogyakarta dan Jawa Tengah", "ga_status": 3},
    ]
    answer, selected = regional_volcano_answer("Daftar gunung api aktif di Jawa Barat", volcanoes)
    assert [item["ga_nama_gapi"] for item in selected] == ["Gede"]
    assert "Gede — Level 2" in answer
    assert "Semeru" not in answer
    assert "Ciremai" not in answer
    assert regional_volcano_answer("Status Gunung Semeru di Jawa Timur", volcanoes) is None
    central, _ = regional_volcano_answer("Gunung api di Jawa Tengah", volcanoes)
    assert "Merapi" in central


def test_region_answer_has_executable_follow_up_candidate(monkeypatch):
    answer = "Gunung api di Jawa Barat (1 gunung):\n1. Gede — Level 2 (Waspada)"
    candidates = follow_ups._api_candidates("Daftar gunung api di Jawa Barat", answer)
    assert candidates[0]["question"] == "Bagaimana status dan rekomendasi resmi untuk Gunung Gede saat ini?"
    monkeypatch.setattr(follow_ups, "model_chat", lambda *args, **kwargs: None)
    suggestion = asyncio.run(follow_ups.DynamicFollowUpGenerator.generate(
        mode="api", question="Daftar gunung api di Jawa Barat", answer=answer,
        references=[], previous=[], model=None,
    ))
    assert suggestion == candidates[0]["question"]


def test_top_three_is_not_confused_with_gunung_paling():
    volcanoes = [
        {"ga_nama_gapi": "Iya", "ga_status": 2},
        {"ga_nama_gapi": "Talang", "ga_status": 1},
        {"ga_nama_gapi": "Semeru", "ga_status": 3},
        {"ga_nama_gapi": "Merapi", "ga_status": 3},
    ]
    answer, chosen = ranked_volcano_answer("Top 3 gunung api paling aktif", volcanoes)
    assert len(chosen) == 3
    assert "tidak memuat peringkat gunung api ‘paling aktif’" in answer
    assert "Gunung Paling" not in answer
    assert "frekuensi erupsi" in answer


def test_short_volcano_reply_uses_exact_name():
    volcanoes = [
        {"ga_nama_gapi": "Iya", "ga_status": 2},
        {"ga_nama_gapi": "Talang", "ga_status": 1, "ga_prov_gapi": "Sumatera Barat"},
    ]
    answer, chosen = named_volcano_answer("Gunung Talang", volcanoes)
    assert chosen[0]["ga_nama_gapi"] == "Talang"
    assert "Level 1 (Normal)" in answer
    assert "Gunung Iya" not in answer
