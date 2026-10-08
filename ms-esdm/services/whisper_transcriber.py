"""Audio transcription service powered by Groq Cloud Whisper API (whisper-large-v3)."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_WHISPER_MODEL = "whisper-large-v3"
VOCAB_PROMPT = (
    "NARA, PVMBG, Badan Geologi, Kementerian ESDM, Gunung Api, Merapi, Semeru, "
    "Sinabung, Bromo, Krakatau, Anak Krakatau, Lewotobi, Ruang, Marapi, gempa bumi, "
    "tsunami, gerakan tanah, MAGMA Indonesia, status siaga, waspada, awas."
)


def get_groq_api_key() -> str:
    """Retrieve Groq API key from environment."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        # Fallback to reading ms-esdm/.env if present
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GROQ_API_KEY="):
                            key = line.strip().split("=", 1)[1].strip()
                            break
            except Exception as e:
                logger.warning("Failed reading .env for GROQ_API_KEY: %s", e)
    return key


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "voice_note.ogg",
    mimetype: str = "audio/ogg",
    language: str = "id",
) -> str:
    """Send audio bytes to Groq Cloud Whisper API for near-instant transcription."""
    api_key = get_groq_api_key()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY belum dikonfigurasi di backend.")

    if not audio_bytes:
        raise ValueError("Data audio kosong.")

    boundary = "----WebKitFormBoundaryGroqWhisper7MA4YWxk"
    body = bytearray()

    # Form field: model
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{DEFAULT_WHISPER_MODEL}\r\n".encode("utf-8"))
    # Form field: language
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\n{language}\r\n".encode("utf-8"))
    # Form field: prompt (biasing vocabulary towards Indonesian geological terms)
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"prompt\"\r\n\r\n{VOCAB_PROMPT}\r\n".encode("utf-8"))
    # Form field: temperature
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"temperature\"\r\n\r\n0.0\r\n".encode("utf-8"))
    # Form field: file
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {mimetype}\r\n\r\n".encode("utf-8"))
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        GROQ_TRANSCRIPTION_URL,
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ESDM-Assistant/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = (data.get("text") or "").strip()
            logger.info("Groq Whisper transcription success: %r", text)
            return text
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        logger.error("Groq Whisper HTTP error %s: %s", exc.code, err_msg)
        raise RuntimeError(f"Gagal transkripsi suara via Groq (HTTP {exc.code}): {err_msg}") from exc
    except Exception as exc:
        logger.error("Groq Whisper connection error: %s", exc)
        raise RuntimeError(f"Gagal menghubungi server transkripsi suara: {exc}") from exc


def transcribe_base64_audio(
    base64_str: str,
    filename: str = "voice_note.ogg",
    mimetype: str = "audio/ogg",
    language: str = "id",
) -> str:
    """Decode base64 audio and transcribe it via Groq Whisper."""
    clean_b64 = base64_str.strip()
    if clean_b64.startswith("data:") and "," in clean_b64:
        header, clean_b64 = clean_b64.split(",", 1)
        if "audio/" in header:
            extracted_mime = header.split(";", 1)[0].replace("data:", "").strip()
            if extracted_mime:
                mimetype = extracted_mime

    audio_bytes = base64.b64decode(clean_b64)
    return transcribe_audio_bytes(audio_bytes, filename=filename, mimetype=mimetype, language=language)

