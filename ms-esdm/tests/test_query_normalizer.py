from utils.query_normalizer import normalize_indonesian_query


def test_informal_query_and_magma_terms():
    result = normalize_indonesian_query("gmn status gn semeru skrg")
    assert result.normalized == "bagaimana status gunung semeru sekarang"


def test_common_typo_is_corrected():
    result = normalize_indonesian_query("gunung api terdejat dgn saya")
    assert result.normalized == "gunung api terdekat dengan saya"


def test_magma_acronyms_are_expanded_for_routing():
    result = normalize_indonesian_query("apa rekomendasi krb dan vona terbaru")
    assert "kawasan rawan bencana" in result.normalized
    assert "peringatan penerbangan abu vulkanik" in result.normalized


def test_names_are_not_aggressively_corrected():
    result = normalize_indonesian_query("status Lewotobi Laki-laki")
    assert "Lewotobi" in result.normalized
