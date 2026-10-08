"""Conservative Indonesian query normalization for MAGMA chat routing."""

import re
from dataclasses import dataclass
from rapidfuzz import fuzz, process


GENERAL_ALIASES = {
    "gmn": "bagaimana",
    "gmna": "bagaimana",
    "gimana": "bagaimana",
    "knp": "kenapa",
    "kenapaa": "kenapa",
    "brp": "berapa",
    "brrp": "berapa",
    "dmn": "di mana",
    "dmna": "di mana",
    "dmana": "di mana",
    "dimn": "di mana",
    "dimna": "di mana",
    "brapa": "berapa",
    "yg": "yang",
    "dgn": "dengan",
    "utk": "untuk",
    "skrg": "sekarang",
    "skrng": "sekarang",
    "saatni": "saat ini",
    "terbaru2": "terbaru",
    "gk": "tidak",
    "ga": "tidak",
    "ngga": "tidak",
    "nggak": "tidak",
    "tdk": "tidak",
    "blm": "belum",
    "udh": "sudah",
    "sdh": "sudah",
    "sy": "saya",
    "aq": "saya",
    "klo": "kalau",
    "kalo": "kalau",
    "bgt": "banget",
    "bngt": "banget",
    "infoin": "informasikan",
}

MAGMA_ALIASES = {
    "gn": "gunung",
    "gng": "gunung",
    "gapi": "gunung api",
    "krb": "kawasan rawan bencana",
    "pga": "pos pengamatan gunung api",
    "pvmbg": "PVMBG",
    "vona": "VONA",
    "var": "VAR",
    "ven": "VEN",
    "erup": "erupsi",
    "erups": "erupsi",
    "abu vulk": "abu vulkanik",
    "gerak tanah": "gerakan tanah",
}

# Fuzzy correction is deliberately limited to routing vocabulary. Arbitrary
# user names and place names must never be autocorrected.
FUZZY_VOCABULARY = (
    "terdekat", "sekarang", "terbaru", "bagaimana", "berapa", "kenapa",
    "gunung", "erupsi", "letusan", "visual", "pengamatan", "aktivitas",
    "status", "siaga", "waspada", "normal", "awas", "longsor",
    "gerakan", "tanah", "gempa", "lokasi", "rekomendasi", "penerbangan",
    "vulkanik", "kawah", "asap", "kolom", "bahaya", "aman",
)


@dataclass(frozen=True)
class NormalizationResult:
    original: str
    normalized: str
    replacements: tuple[tuple[str, str], ...]

    @property
    def changed(self) -> bool:
        return self.original != self.normalized


def _replace_aliases(text: str, aliases: dict[str, str], changes: list[tuple[str, str]]) -> str:
    for source in sorted(aliases, key=len, reverse=True):
        target = aliases[source]
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(target, text)
            changes.append((source, target))
    return text


def normalize_indonesian_query(text: str) -> NormalizationResult:
    original = (text or "").strip()
    normalized = re.sub(r"\s+", " ", original)
    changes: list[tuple[str, str]] = []
    normalized = _replace_aliases(normalized, GENERAL_ALIASES, changes)
    normalized = _replace_aliases(normalized, MAGMA_ALIASES, changes)

    def correct_token(match: re.Match) -> str:
        token = match.group(0)
        lowered = token.lower()
        if len(lowered) < 5 or lowered in FUZZY_VOCABULARY:
            return token
        candidate = process.extractOne(lowered, FUZZY_VOCABULARY, scorer=fuzz.ratio)
        if not candidate:
            return token
        replacement, score, _ = candidate
        if score < 84 or abs(len(lowered) - len(replacement)) > 2:
            return token
        changes.append((token, replacement))
        return replacement

    normalized = re.sub(r"[A-Za-zÀ-ÿ]+", correct_token, normalized)
    normalized = re.sub(r"\s+([?.!,])", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return NormalizationResult(original, normalized, tuple(dict.fromkeys(changes)))
