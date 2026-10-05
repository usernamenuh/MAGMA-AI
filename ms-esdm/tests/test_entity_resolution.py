from services.knowledge_documents_service import (
    _extract_entity_candidates,
    _resolve_document_from_candidates,
    _resolve_entity_from_candidates,
)
from services.pipeline_knowledge import enrich_document_query, get_nara_response


def test_extracts_name_joined_to_phone_number():
    candidates = _extract_entity_candidates([
        "Muhammad Enuh085624139159 | email@example.com Full-Stack Developer"
    ])
    assert "Muhammad Enuh" in candidates


def test_resolves_partial_misspelled_name():
    candidates = ["Muhammad Enuh", "Roni Hermawan"]
    result = _resolve_entity_from_candidates("Nuh sekolah dimana", candidates)
    assert result["status"] == "resolved"
    assert result["entity"] == "Muhammad Enuh"


def test_resolves_two_misspelled_name_tokens():
    candidates = ["Muhammad Enuh", "Roni Hermawan"]
    result = _resolve_entity_from_candidates(
        "Mohamad Nuh riwayat pendidikan", candidates
    )
    assert result["status"] == "resolved"
    assert result["entity"] == "Muhammad Enuh"


def test_ignores_conversational_words_around_misspelled_name():
    result = _resolve_entity_from_candidates(
        "Apakah anda tahu mohamad nuh", ["Muhammad Enuh", "Roni Hermawan"]
    )
    assert result["status"] == "resolved"
    assert result["entity"] == "Muhammad Enuh"


def test_allows_one_noisy_name_token_when_surname_is_exact():
    result = _resolve_entity_from_candidates(
        "Apakah tahu mocahamad enuh", ["Muhammad Enuh", "Roni Hermawan"]
    )
    assert result["status"] == "resolved"
    assert result["entity"] == "Muhammad Enuh"


def test_does_not_force_unrelated_question_to_an_entity():
    result = _resolve_entity_from_candidates(
        "jelaskan isi dokumen", ["Muhammad Enuh", "Roni Hermawan"]
    )
    assert result is None


def test_reports_ambiguous_partial_name():
    result = _resolve_entity_from_candidates(
        "Muhammad bekerja dimana", ["Muhammad Enuh", "Muhammad Rizki"]
    )
    assert result["status"] == "ambiguous"
    assert set(result["candidates"]) == {"Muhammad Enuh", "Muhammad Rizki"}


def test_resolves_abbreviated_first_name_with_unrelated_words():
    result = _resolve_entity_from_candidates(
        "UAS Muti apa sih isinya", ["Mutiara Awaliah", "Roni Hermawan"]
    )
    assert result["status"] == "resolved"
    assert result["entity"] == "Mutiara Awaliah"


def test_resolves_abbreviated_document_filename_generically():
    result = _resolve_document_from_candidates(
        "Mutiara UAS-nya bikin apa?",
        [
            (50, "Mutiara_Awaliah_24020015_A2024_UUD1945.docx"),
            (51, "Laporan_Mitigasi_Gunung_Merapi.pdf"),
        ],
    )
    assert result["status"] == "resolved"
    assert result["document_id"] == 50


def test_document_resolution_asks_when_abbreviation_is_ambiguous():
    result = _resolve_document_from_candidates(
        "laporan Mer isinya apa",
        [(1, "Laporan_Merapi.pdf"), (2, "Laporan_Merbabu.pdf")],
    )
    assert result["status"] == "ambiguous"


def test_rewrites_conversational_overview_question():
    search_query, answer_query = enrich_document_query("Mutiara UAS-nya bikin apa?")
    assert "abstrak" in search_query
    assert "isi utama" in answer_query


def test_nara_introduces_itself_for_greeting():
    assert "NARA ESDM" in get_nara_response("Halo")
    assert "NARA ESDM" in get_nara_response("Hallo")


def test_nara_clarifies_context_free_message():
    assert "belum cukup jelas" in get_nara_response("Tolong jelaskan")


def test_follow_up_and_specific_question_go_to_document_pipeline():
    assert get_nara_response("Pendidikannya apa?", has_history=True) is None
    assert get_nara_response("Nuh sekolah di mana?") is None
