"""Text-to-Speech (TTS) service using Microsoft Edge Neural Voice (edge-tts)."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import urllib.request
from typing import Optional

import edge_tts

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "id-ID-GadisNeural"  # Professional, natural Indonesian female voice
MALE_VOICE = "id-ID-ArdiNeural"       # Indonesian male voice
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "esdm-demo-evolution-key-change-before-public")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "esdm-assistant")


def prepare_text_for_speech(text: str, max_chars: int = 500) -> str:
    """Transform markdown and technical WhatsApp response into natural, speakable Indonesian."""
    if not text or not text.strip():
        return ""

    # 1. Strip transcribed user voice note quote header
    t = re.sub(r'🎙️\s*Pesan Suara:\s*"[^"]*"\s*', '', text)

    # 2. Strip interactive follow-up invitations
    t = re.sub(r'💬\s*Apakah Anda ingin tahu[\s\S]*$', '', t)
    t = re.sub(r'Balas ya jika ingin NARA lanjutkan[\s\S]*$', '', t)

    # 3. Strip URLs / Google Maps links
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'(?:Link Peta|Titik Koordinat):\s*', '', t, flags=re.I)

    # 4. Remove emojis and Unicode pictographs
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u2600-\u27bf]', '', t)

    # 5. Clean abbreviations & technical units for clear pronunciation
    t = re.sub(r'\bPVMBG\b', 'P V M B G', t)
    t = re.sub(r'\bESDM\b', 'E S D M', t)
    t = re.sub(r'\bKRB\b', 'Kawasan Rawan Bencana', t)
    level_names = {"I": "satu", "II": "dua", "III": "tiga", "IV": "empat"}
    t = re.sub(
        r'\bLevel\s+(IV|III|II|I)\b',
        lambda match: f"Level {level_names[match.group(1).upper()]}",
        t,
        flags=re.I,
    )
    t = re.sub(r'\bkm\b', ' kilometer', t)
    t = re.sub(r'(\d+)\s*m\b', r'\1 meter', t)
    t = re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3-\2-\1', t)

    # 6. Remove asterisks, hashtags, bullets, and markdown artifacts
    t = re.sub(r'[*#_`~]', '', t)
    t = re.sub(r'^\s*[-•]\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'\n+', '. ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # 7. If text is excessively long, truncate gracefully and add closing remark
    if len(t) > max_chars:
        sentences = re.split(r'(?<=[.!?])\s+', t)
        shortened = []
        curr_len = 0
        for s in sentences:
            if curr_len + len(s) > max_chars and shortened:
                break
            shortened.append(s)
            curr_len += len(s)
        t = " ".join(shortened).strip()
        if not t.endswith("."):
            t += "."
        t += " Rincian lengkap dan rekomendasinya dapat disimak pada pesan teks ya."

    return t


async def generate_speech_audio(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """Generate MP3 audio bytes using Microsoft Edge Neural Voice."""
    clean_text = prepare_text_for_speech(text)
    if not clean_text:
        return b""

    communicate = edge_tts.Communicate(clean_text, voice=voice)
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio_data.extend(chunk.get("data", b""))

    return bytes(audio_data)


async def send_whatsapp_voice_note(
    number: str,
    text: str,
    voice: str = DEFAULT_VOICE,
    delay: int = 1000,
) -> bool:
    """Generate speech and send it as a native WhatsApp Voice Note (PTT) via Evolution API."""
    clean_number = number.strip().replace("@s.whatsapp.net", "").replace("@lid", "")
    if ":" in clean_number:
        clean_number = clean_number.split(":", 1)[0]

    try:
        audio_bytes = await generate_speech_audio(text, voice=voice)
        if not audio_bytes:
            logger.warning("Empty audio bytes generated for TTS")
            return False

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        url = f"{EVOLUTION_API_URL.rstrip('/')}/message/sendWhatsAppAudio/{EVOLUTION_INSTANCE}"

        payload = {
            "number": clean_number,
            "audio": b64_audio,
            "delay": delay,
            "encoding": True,
        }

        def _do_post():
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "apikey": EVOLUTION_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status

        status = await asyncio.to_thread(_do_post)
        print(f"🎤 [TTS] Berhasil mengirim Voice Note WhatsApp ke {clean_number} (HTTP {status})", flush=True)
        return status in (200, 201)
    except Exception as exc:
        print(f"❌ [TTS] Gagal mengirim Voice Note WhatsApp ke {clean_number}: {exc}", flush=True)
        return False
