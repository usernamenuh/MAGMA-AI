"""AI Agent Router & Decision Engine for MAGMA AI Assistant.

Architecture:
1. Decision Router:
   - Accurately classifies user intent without conflicting regex traps.
   - Extracts parameters (volcano code, target volcano, place, etc.).
2. Dedicated Tools with Strict API Response Validation:
   - LocationTool: Geolocation, nearest volcano, hazard radius assessment.
   - VolcanoEruptionTool: Queries VEN API with query-param validation; handles both recorded eruptions and mountains with no recent VEN records.
   - VolcanoStatusTool: Queries VAR / status level & PVMBG recommendations.
   - VolcanoActiveListTool: Groups active/elevated volcanoes (Level III & II).
   - EarthquakeTool: Latest and list of significant earthquakes.
   - EarthquakeMitigationTool: Official PVMBG & BMKG safety guidelines.
   - GroundMovementTool: Landslide / gerakan tanah reports.
   - ConversationalTool: Greetings, identity, capability.
3. Intelligent Follow-Up Generator:
   - LLM + conversation memory + intent + source context + structured output.
   - Never repeats past topics; moves conversation forward logically.
"""
from __future__ import annotations

import json
import logging
import re
import html
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz
from mistralai.models.chat_completion import ChatMessage
from utils.follow_ups import extract_executed_topics
from services.knowledge_documents_service import KnowledgeDocumentsService
from utils.extraction import detect_volcano_name
from utils.geo_location import extract_indonesia_location, get_geolocation_indonesia
from utils.location_answers import (
    build_location_answer,
    detect_location_question,
    missing_location_answer,
)
from utils.pipeline_helpers import (
    BASE_URL,
    _detect_volcano_name,
    call_api,
    check_if_mount_level,
    find_nearest_volcano,
    get_earthquake_list,
    get_geohazard_location_awareness,
    get_ground_movement_list,
    get_latest_earthquake_data,
    get_latest_ground_movement_data,
    get_mount_code,
    get_today_eruption_events,
    get_volcano_var_data,
    load_volcano_cache,
    model_chat,
    resolve_api_url,
    STOPWORDS,
)
from services.check_status_magma import (
    filter_data_by_intent,
    format_volcano_status_markdown,
    return_status,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. DEDICATED TOOLS WITH STRICT RESPONSE VALIDATION
# ---------------------------------------------------------------------------

class LocationTool:
    """Tool for device geolocation, nearest volcano calculation, and hazard safety assessment."""

    @staticmethod
    def execute(
        user_input: str,
        geo_location: Optional[Tuple[float, float]],
        location_name: Optional[str] = None,
        location_accuracy: Optional[float] = None,
        history: str = "",
        lang: str = "id",
    ) -> Dict[str, Any]:
        volcano_resp = get_mount_code() or load_volcano_cache() or []
        loc_mode = detect_location_question(user_input, lang) or "safety"

        eff_geo = None
        eff_name = location_name
        eff_accuracy = location_accuracy

        # If user asks about own position and device coordinates are available, prioritize them
        is_asking_own_pos = bool(
            re.search(r"\b(saya|aku|kami|kita|sini|disini|posisi\s+saya|lokasi\s+saya)\b", user_input, re.IGNORECASE)
        )
        if is_asking_own_pos and geo_location and any(geo_location):
            try:
                eff_geo = (float(geo_location[0]), float(geo_location[1]))
            except (TypeError, ValueError):
                eff_geo = None

        if not eff_geo:
            sanitized_for_loc = re.sub(
                r"\b(?:gunung(?:\s+api)?|gn\.|mount|mt\.)\s+[a-zA-Z\s\-]+", "", user_input, flags=re.IGNORECASE
            )
            extracted_loc = extract_indonesia_location(sanitized_for_loc)
            if extracted_loc:
                loc_coords = get_geolocation_indonesia(extracted_loc)
                if loc_coords and any(loc_coords):
                    eff_geo = (float(loc_coords[0]), float(loc_coords[1]))
                    eff_name = extracted_loc
                    eff_accuracy = None

        if not eff_geo and geo_location and any(geo_location):
            try:
                eff_geo = (float(geo_location[0]), float(geo_location[1]))
            except (TypeError, ValueError):
                eff_geo = None

        if not eff_geo:
            return {
                "status": "success",
                "output": missing_location_answer(lang),
                "api_call": None,
                "response": None,
                "geo_location": None,
                "intent": "LOCATION_SAFETY",
            }

        # Resolve target volcano from query or conversation history
        target_volcano_name = None
        v_match = re.search(r"gunung\s+([a-zA-Z\s\-]+?)(?:\?|$|\s+berjarak|\s+aman)", user_input, re.IGNORECASE)
        if v_match:
            cand = v_match.group(1).strip()
            if cand.lower() not in {"api", "berapi", "terdekat", "saya", "aktif", "ini"}:
                target_volcano_name = cand
        if not target_volcano_name and history:
            prev_v = re.findall(
                r"(?:Gunung|Mount)\s+([A-Z][a-zA-Z\s\-]+?)(?:\s+adalah|\s+berstatus|\s+berjarak|\?|\.|\,)",
                history,
            )
            if prev_v:
                cand = prev_v[-1].strip()
                if cand.lower() not in {"api", "berapi", "terdekat", "aktif", "di indonesia"}:
                    target_volcano_name = cand

        out_text, nearest_items = build_location_answer(
            mode=loc_mode,
            lat=eff_geo[0],
            lon=eff_geo[1],
            volcano_list=volcano_resp,
            location_name=eff_name,
            accuracy_m=eff_accuracy,
            lang=lang,
            target_volcano_name=target_volcano_name,
        )

        return {
            "status": "success",
            "output": out_text,
            "api_call": f"{BASE_URL}/api/v2/volcano/list",
            "response": nearest_items,
            "geo_location": eff_geo,
            "nearest_volcano": nearest_items[0] if nearest_items else None,
            "intent": "LOCATION_SAFETY",
        }


class VolcanoEruptionTool:
    """Tool for volcano eruption history, latest eruptions, and today's eruption events."""

    @staticmethod
    def execute(
        volcano_code: Optional[str],
        volcano_name: Optional[str],
        user_input: str,
        volcano_resp: List[Dict[str, Any]],
        lang: str = "id",
    ) -> Dict[str, Any]:
        # Check if user asks about today's eruption summary across Indonesia
        is_today = bool(re.search(r"\b(hari ini|today|sekarang|saat ini)\b", user_input, re.IGNORECASE))
        if not volcano_code and is_today:
            eruption_data = get_today_eruption_events()
            events = eruption_data.get("events", [])
            if not events:
                output_text = "Belum ada catatan kejadian letusan/erupsi baru yang terekam dalam data MAGMA Indonesia untuk hari ini."
            else:
                volcano_names = sorted({e.get("nama_gunung_api") for e in events if e.get("nama_gunung_api")})
                output_text = (
                    f"Hari ini tercatat {len(events)} kejadian erupsi dari {len(volcano_names)} gunung api: "
                    f"{', '.join(volcano_names)}."
                )
            return {
                "status": "success",
                "output": output_text,
                "api_call": f"{BASE_URL}/api/v2/volcano/ven",
                "response": events,
                "intent": "VOLCANO_ERUPTION",
            }

        # Specific volcano eruption inquiry
        api_url = f"{BASE_URL}/api/v2/volcano/ven/filter"
        clean_code = volcano_code.strip().upper() if volcano_code else "KRA"
        resp = call_api(api_url, method="GET", params={"code": clean_code})

        # STRICT API RESPONSE VALIDATION
        v_data = resp.get("data", []) if isinstance(resp, dict) else []
        display_name = volcano_name or clean_code

        # If the volcano exists in the list, get official name and status
        matched_v = next((v for v in volcano_resp if (v.get("ga_code") or "").upper() == clean_code), None)
        if matched_v:
            display_name = matched_v.get("ga_nama_gapi") or display_name
            status_code = matched_v.get("ga_status", 1)
        else:
            status_code = 1

        status_labels = {
            1: "Level I (Normal)",
            2: "Level II (Waspada)",
            3: "Level III (Siaga)",
            4: "Level IV (Awas)",
        }
        status_label = status_labels.get(status_code, f"Level {status_code}")

        if isinstance(v_data, list) and len(v_data) > 0:
            latest = v_data[0]
            dt_str = latest.get("local_datetime") or f"{latest.get('local_date', '')} {latest.get('local_time', '')} {latest.get('time_zone', '')}".strip()
            visual_desc = (latest.get("deskripsi") or {}).get("visual") if isinstance(latest.get("deskripsi"), dict) else None
            tingkat = latest.get("tingkat_aktivitas") or status_label
            rekom = latest.get("rekomendasi") or (matched_v.get("ga_rekomendasi") if matched_v else None)

            lines = [f"🌋 Catatan Erupsi Terakhir Gunung {display_name} (PVMBG):"]
            if visual_desc:
                lines.append(visual_desc)
            else:
                lines.append(f"Terekam kejadian erupsi pada {dt_str}.")
            lines.append(f"Status Aktivitas Saat Ini: {tingkat}")
            if rekom:
                clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rekom)).strip()
                lines.append(f"📋 Rekomendasi Resmi PVMBG:\n{clean_rek}")

            return {
                "status": "success",
                "output": "\n".join(lines),
                "api_call": api_url,
                "response": v_data,
                "intent": "VOLCANO_ERUPTION",
            }
        else:
            # VALIDATION: No eruption events in VEN database (e.g. Gunung Slamet)
            var_data = get_volcano_var_data(clean_code)
            rekom = None
            if var_data and isinstance(var_data, dict):
                lap = var_data.get("laporan_terakhir") or {}
                rekom = lap.get("rekomendasi")

            lines = [
                f"🌋 Informasi Catatan Erupsi Gunung {display_name} (PVMBG):",
                f"Berdasarkan basis data laporan letusan resmi PVMBG (MAGMA Indonesia), saat ini **belum ada catatan kejadian letusan/erupsi baru yang terekam untuk Gunung {display_name}** pada sistem informasi letusan terkini (VEN).",
                f"Status Aktivitas Saat Ini: **{status_label}**.",
            ]
            if matched_v:
                loc = ", ".join(filter(None, [matched_v.get("ga_kab_gapi"), matched_v.get("ga_prov_gapi")]))
                if loc:
                    lines.append(f"Lokasi: {loc}.")
            if rekom:
                clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rekom)).strip()
                lines.append(f"📋 Rekomendasi Resmi PVMBG:\n{clean_rek}")

            return {
                "status": "success",
                "output": "\n".join(lines),
                "api_call": api_url,
                "response": [],
                "intent": "VOLCANO_ERUPTION",
            }


class VolcanoStatusTool:
    """Tool for official PVMBG volcanic alert status and recommendations for specific volcanoes."""

    @staticmethod
    def execute(
        volcano_code: str,
        volcano_resp: List[Dict[str, Any]],
        user_input: str = "",
        lang: str = "id",
    ) -> Dict[str, Any]:
        clean_code = volcano_code.strip().upper()
        matched = [v for v in volcano_resp if (v.get("ga_code") or "").upper() == clean_code]

        status_labels = {
            1: "Level I (Normal)",
            2: "Level II (Waspada)",
            3: "Level III (Siaga)",
            4: "Level IV (Awas)",
        }

        if not matched:
            return {
                "status": "error",
                "output": "Data status gunung api yang diminta tidak ditemukan dalam database PVMBG.",
                "api_call": f"{BASE_URL}/api/v2/volcano/list",
                "response": None,
                "intent": "VOLCANO_STATUS",
            }

        lines = []
        is_rec_only = bool(re.search(r"\b(rekomendasi(nya)?|anjuran|arahan|himbauan)\b", user_input, re.IGNORECASE)) and not bool(re.search(r"\b(status|level|kondisi)\b", user_input, re.IGNORECASE))
        for v in matched:
            name = v.get("ga_nama_gapi") or clean_code
            level = v.get("ga_status", 1)
            loc = ", ".join(filter(None, [v.get("ga_kab_gapi"), v.get("ga_prov_gapi")]))
            var_data = get_volcano_var_data(clean_code)
            clean_rek = None
            tgl = None
            if var_data and isinstance(var_data, dict):
                lap = var_data.get("laporan_terakhir") or {}
                rek = lap.get("rekomendasi")
                tgl = lap.get("tanggal")
                if rek:
                    clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rek)).strip()

            if is_rec_only and clean_rek:
                lines.append(
                    f"📋 Rekomendasi Resmi PVMBG untuk Gunung {name} ({status_labels.get(level, f'Level {level}')})"
                    + (f" [{tgl}]:\n\n" if tgl else ":\n\n")
                    + clean_rek
                )
            else:
                lines.append(
                    f"Status aktivitas Gunung {name} adalah {status_labels.get(level, f'Level {level}')}."
                    + (f" Lokasi: {loc}." if loc else "")
                )
                if clean_rek:
                    lines.append(
                        f"\n📋 Rekomendasi Resmi PVMBG"
                        + (f" ({tgl}):\n" if tgl else ":\n")
                        + clean_rek
                    )

        return {
            "status": "success",
            "output": "\n".join(lines),
            "api_call": f"{BASE_URL}/api/v2/volcano/list",
            "response": matched,
            "intent": "VOLCANO_STATUS",
        }


class VolcanoActiveListTool:
    """Tool for aggregate list of active and elevated volcanoes across Indonesia."""

    @staticmethod
    def execute(user_input: str) -> Dict[str, Any]:
        volcanoes = get_mount_code() or load_volcano_cache() or []
        output_text = return_status(user_input)
        if not output_text or "Tidak ditemukan" in output_text:
            data = filter_data_by_intent(volcanoes, "ACTIVE_ELEVATED")
            output_text = format_volcano_status_markdown(data, "ACTIVE_ELEVATED")
        return {
            "status": "success",
            "output": output_text,
            "api_call": f"{BASE_URL}/api/v2/volcano/list",
            "response": volcanoes,
            "intent": "VOLCANO_ACTIVE_LIST",
        }


class EarthquakeTool:
    """Tool for earthquake and tsunami reports and geological analysis from PVMBG & BMKG."""

    @staticmethod
    def execute(user_input: str, geo_location: Optional[Tuple[float, float]]) -> Dict[str, Any]:
        is_list = bool(re.search(r"\b(daftar|list|lainnya|semua|apa saja|riwayat|beberapa)\b", user_input, re.IGNORECASE))
        extracted_place = extract_indonesia_location(user_input)

        if is_list:
            eq_list = get_earthquake_list()
            answer_parts = []
            if eq_list:
                answer_parts.append("📋 Daftar Kejadian Gempa Bumi Penting Terbaru (Badan Geologi / PVMBG):")
                for i, item in enumerate(eq_list[:5], 1):
                    judul = item.get("judul", "Kejadian Gempa Bumi").strip()
                    dt = item.get("local_datetime") or item.get("date") or ""
                    mag = item.get("magnitude")
                    mag_str = f"M {mag} — " if mag else ""
                    dt_str = f" [{dt}]" if dt else ""
                    short_judul = re.sub(r"^ANALISIS GEOLOGI KEJADIAN GEMPA BUMI DI\s+", "", judul, flags=re.IGNORECASE)
                    short_judul = re.sub(r"\s+TANGGAL.*$", "", short_judul, flags=re.IGNORECASE).strip()
                    answer_parts.append(f"{i}. {mag_str}{short_judul}{dt_str}")
            else:
                answer_parts.append("Belum ada daftar kejadian gempa bumi penting lainnya yang dapat ditampilkan saat ini.")

            return {
                "status": "success",
                "output": "\n\n".join(answer_parts),
                "api_call": resolve_api_url("/api/v2/earthquake-tsunami"),
                "response": eq_list,
                "intent": "EARTHQUAKE",
            }
        else:
            eq = get_latest_earthquake_data()
            answer_parts = []
            if eq and eq.get("judul"):
                source = eq.get("source", "MAGMA ESDM")
                judul = eq.get("judul")
                dt = eq.get("datetime")
                mag = eq.get("magnitude")
                depth = eq.get("kedalaman")
                lok = eq.get("lokasi") or eq.get("kota_terdekat")
                tsunami_str = "Berpotensi tsunami" if eq.get("tsunami") else "Tidak berpotensi tsunami"

                details_str = f"Waktu: {dt}, Magnitudo: M {mag}, Kedalaman: {depth} km, Wilayah: {lok}. Status: {tsunami_str}."
                answer_parts.append(f"Catatan gempa terkini ({source}):\n{judul}\n{details_str}")

                rek = eq.get("rekomendasi")
                if rek:
                    clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rek)).strip()
                    if len(clean_rek) > 280:
                        clean_rek = clean_rek[:280] + "..."
                    answer_parts.append(f"📋 Rekomendasi Resmi:\n{clean_rek}")
            else:
                answer_parts.append("Belum ada laporan kejadian gempa bumi signifikan terbaru yang tercatat. Pantau kanal resmi Badan Geologi dan BMKG.")

            return {
                "status": "success",
                "output": "\n\n".join(answer_parts),
                "api_call": resolve_api_url("/api/v2/earthquake-tsunami"),
                "response": eq,
                "intent": "EARTHQUAKE",
            }


class EarthquakeMitigationTool:
    """Tool for official earthquake safety and mitigation guidance."""

    @staticmethod
    def execute() -> Dict[str, Any]:
        text = (
            "📋 Panduan Langkah Mitigasi & Keselamatan Gempa Bumi (PVMBG & BMKG):\n\n"
            "1. Saat Terjadi Guncangan:\n"
            "   • Berlindung di bawah meja yang kokoh (*Drop, Cover, Hold On*) dan lindungi kepala serta leher.\n"
            "   • Jauhi jendela kaca, lemari tinggi, dan benda gantung yang berpotensi jatuh.\n"
            "   • Jika berada di luar ruangan, cari area terbuka yang jauh dari bangunan tinggi, tiang listrik, dan tebing curam.\n"
            "   • Jika berada di pesisir pantai dan merasakan gempa kuat atau berayun lama, segera evakuasi ke dataran tinggi tanpa menunggu sirine.\n\n"
            "2. Setelah Guncangan Mereda:\n"
            "   • Waspadai potensi gempa bumi susulan (*aftershocks*).\n"
            "   • Matikan kompor dan periksa instalasi listrik/gas guna mencegah kebakaran.\n"
            "   • Gunakan tangga darurat untuk keluar bangunan, jangan pernah menggunakan lift.\n"
            "   • Pantau informasi resmi hanya dari Badan Geologi (PVMBG) dan BMKG."
        )
        return {
            "status": "success",
            "output": text,
            "api_call": resolve_api_url("/api/v2/earthquake-tsunami"),
            "response": None,
            "intent": "EARTHQUAKE_MITIGATION",
        }


class GroundMovementMitigationTool:
    """Tool for official ground movement and landslide safety and mitigation guidance."""

    @staticmethod
    def execute() -> Dict[str, Any]:
        text = (
            "📋 Panduan Lengkap Mitigasi Bencana Gerakan Tanah & Tanah Longsor (PVMBG - Badan Geologi, Kementerian ESDM):\n\n"
            "1. Kesiapsiagaan & Pencegahan (Pra-Bencana):\n"
            "   • Kenali Gejala & Tanda Awal Gerakan Tanah / Longsor:\n"
            "     - Muncul retakan tanah melengkung atau memanjang pada lereng, jalan, atau dinding dan lantai rumah.\n"
            "     - Tiang listrik, pohon, atau tiang pagar mulai miring secara tidak wajar.\n"
            "     - Pintu atau jendela mendadak sulit dibuka/ditutup akibat pergeseran struktur bangunan.\n"
            "     - Air sumur atau mata air mendadak keruh berlumpur, atau muncul rembesan air baru di tebing lereng.\n"
            "     - Terdengar suara gemuruh kecil atau runtuhan material kerikil dari arah tebing perbukitan.\n"
            "   • Tindakan Fisik & Tata Ruang Lingkungan:\n"
            "     - Jangan mendirikan bangunan tempat tinggal di lereng curam, di bawah tebing terjal, atau di bantaran alur sungai longsor.\n"
            "     - Buat dan pelihara sistem drainase lereng agar air hujan mengalir tuntas dan tidak meresap menjenuhkan lereng.\n"
            "     - Hindari memotong lereng secara tegak lurus tanpa dinding penahan (retaining wall) dan perkuatan struktur.\n"
            "     - Tanam tanaman berakar dalam dan mengikat tanah (seperti akar wangi/vetiver, bambu, aren) di kawasan lereng rawan.\n\n"
            "2. Tindakan Saat Terjadi Longsor (Tanggap Darurat):\n"
            "   • Segera evakuasi menjauhi lereng atau jalur longsor menuju tempat terbuka yang datar dan stabil.\n"
            "   • Berikan peringatan bahaya (bunyikan sirine/kentongan) untuk memperingatkan warga lain jika memungkinkan tanpa membahayakan diri.\n"
            "   • Jangan mendekati material runtuhan longsor karena sangat berisiko tinggi terjadi longsor susulan.\n"
            "   • Jika terjebak di dalam bangunan, lindungi kepala dan leher dalam posisi meringkuk di bawah perabot kokoh.\n\n"
            "3. Tindakan Pasca-Bencana:\n"
            "   • Waspadai potensi longsor susulan, terutama jika hujan lebat masih terus turun.\n"
            "   • Jangan langsung memasuki rumah yang rusak atau berada di lereng terdampak sebelum diperiksa oleh tim ahli geologi atau BPBD.\n"
            "   • Periksa jalur instalasi listrik, pipa air, dan tabung gas guna menghindari bahaya kebakaran sekunder.\n"
            "   • Pantau terus pembaruan informasi dan arahan resmi dari Badan Geologi (PVMBG) dan BPBD setempat."
        )
        return {
            "status": "success",
            "output": text,
            "api_call": resolve_api_url("/api/v2/ground-movement"),
            "response": None,
            "intent": "GROUND_MOVEMENT_MITIGATION",
        }


class GroundMovementTool:
    """Tool for ground movement (landslides) emergency response reports."""

    @staticmethod
    def execute(user_input: str) -> Dict[str, Any]:
        is_list = bool(re.search(r"\b(daftar|list|semua|riwayat|beberapa)\b", user_input, re.IGNORECASE))
        if is_list:
            gm_list = get_ground_movement_list()
            answer_parts = []
            if gm_list:
                answer_parts.append("📋 Daftar Laporan Tanggapan Gerakan Tanah / Tanah Longsor Terbaru (Badan Geologi):")
                for i, item in enumerate(gm_list[:5], 1):
                    judul = item.get("judul", "Laporan Gerakan Tanah").strip()
                    dt = item.get("datetime") or item.get("tanggal") or ""
                    short_judul = re.sub(r"^LAPORAN SINGKAT PEMERIKSAAN GERAKAN TANAH DI\s+", "", judul, flags=re.IGNORECASE).strip()
                    answer_parts.append(f"{i}. {short_judul} [{dt}]")
            else:
                answer_parts.append("Belum ada daftar laporan tanggapan gerakan tanah yang dapat ditampilkan saat ini.")

            return {
                "status": "success",
                "output": "\n\n".join(answer_parts),
                "api_call": resolve_api_url("/api/v2/ground-movement"),
                "response": gm_list,
                "intent": "GROUND_MOVEMENT",
            }
        else:
            gm_data = get_latest_ground_movement_data()
            answer_parts = []
            if gm_data and gm_data.get("judul"):
                judul = gm_data.get("judul").strip()
                dt = gm_data.get("datetime", "")
                pelapor = gm_data.get("pelapor", "")
                tipe = gm_data.get("tipe") or "Gerakan Tanah / Tanah Longsor"
                answer_parts.append(
                    f"Laporan Tanggap Darurat Gerakan Tanah Terbaru (Badan Geologi):\n"
                    f"📌 {judul}\n"
                    f"Waktu Laporan: {dt} | Pelapor: {pelapor}\n"
                    f"Tipe Gerakan: {tipe}"
                )
                kondisi = gm_data.get("kondisi") or {}
                penyebab = kondisi.get("penyebab")
                if penyebab:
                    clean_penyebab = html.unescape(re.sub(r"<[^>]+>", " ", penyebab)).strip()
                    answer_parts.append(f"Faktor Penyebab: {clean_penyebab}")
                rek_list = gm_data.get("rekomendasi")
                if rek_list:
                    clean_reks = []
                    for r in (rek_list if isinstance(rek_list, list) else [rek_list]):
                        c = html.unescape(re.sub(r"<[^>]+>", " ", str(r))).strip()
                        c = re.sub(r"\s+", " ", c)
                        if len(c) > 35 and not re.match(r"^(\d+\.?)?\s*(kesimpulan|rekomendasi)\s*$", c, re.IGNORECASE):
                            clean_reks.append(c)
                    if clean_reks:
                        summary_rek = clean_reks[0][:280] + "..." if len(clean_reks[0]) > 280 else clean_reks[0]
                        answer_parts.append(f"📌 Rekomendasi / Arahan Ahli:\n{summary_rek}")
            else:
                answer_parts.append("Belum ada laporan kejadian gerakan tanah terbaru yang tercatat di sistem saat ini.")

            return {
                "status": "success",
                "output": "\n\n".join(answer_parts),
                "api_call": resolve_api_url("/api/v2/ground-movement/latest"),
                "response": gm_data.get("raw") if gm_data else None,
                "intent": "GROUND_MOVEMENT",
            }


OFFICIAL_PVMBG_KNOWLEDGE_DOCS = [
    {
        "id": "status_levels_full",
        "title": "Pedoman Standar Tingkat Aktivitas Gunung Api (PVMBG - Badan Geologi)",
        "matches": lambda q: bool(
            re.search(r"\b(tingkat(?:an)?|status|level)\b.*?\b(normal|waspada|siaga|awas)\b", q.lower())
            or re.search(r"\b(arti|maksud|definisi|pengertian|penjelasan|jelaskan)\b.*?\b(tingkat(?:an)?|status|level)\b", q.lower())
            or re.search(r"\b(beda|perbedaan)\b.*?\b(waspada|siaga|awas|normal)\b", q.lower())
            or re.search(r"\btingkat(?:an)?\s+status\b", q.lower())
        ),
        "content": (
            "Berdasarkan standar Pusat Vulkanologi dan Mitigasi Bencana Geologi (PVMBG), Badan Geologi, Kementerian ESDM, tingkat aktivitas gunung api di Indonesia dibagi menjadi 4 level:\n\n"
            "1. **Level I (Normal)**:\n"
            "- **Definisi/Arti**: Aktivitas vulkanik berada pada tingkat dasar (baseline). Berdasarkan pengamatan visual dan instrumental (kegempaan dan deformasi), tidak ada indikasi peningkatan aktivitas vulkanik.\n"
            "- **Potensi Bahaya**: Sangat minimal, ancaman bahaya umumnya terbatas pada potensi gas beracun atau erupsi freatik lokal di dasar kawah aktif.\n"
            "- **Rekomendasi**: Masyarakat dan wisatawan aman beraktivitas normal, namun diimbau tidak menuruni atau bermalam di dasar kawah aktif.\n\n"
            "2. **Level II (Waspada)**:\n"
            "- **Definisi/Arti**: Mulai teramati adanya peningkatan aktivitas di atas level normal, baik secara visual maupun kegempaan (peningkatan gempa vulkanik dangkal/dalam atau deformasi) akibat kenaikan dinamika magma/fluida hidrotermal.\n"
            "- **Potensi Bahaya**: Potensi bahaya melingkupi area kawah (Kawasan Rawan Bencana III), seperti letusan freatik tiba-tiba atau lontaran material pijar lokal.\n"
            "- **Rekomendasi**: Masyarakat, wisatawan, dan pendaki dilarang mendekati kawah dalam radius yang ditetapkan PVMBG (umumnya radius 1–3 km).\n\n"
            "3. **Level III (Siaga)**:\n"
            "- **Definisi/Arti**: Peningkatan aktivitas vulkanik berlangsung nyata dan signifikan. Pengamatan instrumental menunjukkan kecenderungan letusan berpeluang besar terjadi dalam waktu dekat atau erupsi awal sudah dimulai.\n"
            "- **Potensi Bahaya**: Ancaman bahaya dapat meluas ke Kawasan Rawan Bencana II.\n"
            "- **Rekomendasi**: Jalur pendakian ditutup total, sosialisasi evakuasi ditingkatkan, dan masyarakat di sekitar zona bahaya harus siap siaga melakukan evakuasi.\n\n"
            "4. **Level IV (Awas)**:\n"
            "- **Definisi/Arti**: Kondisi kritis di mana letusan utama sedang berlangsung atau erupsi besar/dahsyat akan segera terjadi dalam hitungan waktu singkat.\n"
            "- **Potensi Bahaya**: Sangat berbahaya, mengancam permukiman di seluruh Kawasan Rawan Bencana (KRB I, II, dan III) berupa awan panas guguran, lontaran batu pijar, aliran lava, dan hujan abu lebat.\n"
            "- **Rekomendasi**: Seluruh penduduk di dalam zona bahaya yang ditetapkan wajib segera dievakuasi ke tempat penampungan yang aman."
        ),
    },
    {
        "id": "status_level_2",
        "title": "Karakteristik & Arti Status Level II (Waspada) PVMBG",
        "matches": lambda q: bool(
            re.search(r"\b(level\s+(?:ii|2)|waspada)\b", q.lower())
            and re.search(r"\b(arti|maksud|definisi|pengertian|apa\s+itu|jelaskan|kriteria)\b", q.lower())
        ),
        "content": (
            "**Arti dan Karakteristik Status Level II (Waspada)** menurut standar PVMBG - Badan Geologi:\n\n"
            "1. **Arti**: Gunung api mengalami peningkatan aktivitas di atas tingkat normal/dasar (baseline). Hal ini ditandai dengan kenaikan aktivitas seismik (gempa vulkanik dangkal/dalam), hembusan asap kawah yang lebih tebal/tinggi, atau perubahan deformasi/suhu kawah.\n"
            "2. **Potensi Bahaya**: Bahaya utama terkonsentrasi di sekitar kawah aktif (Kawasan Rawan Bencana III), meliputi letusan freatik tanpa peringatan, emisi gas vulkanik beracun, dan lontaran batu/material pijar lokal di puncak.\n"
            "3. **Tindakan & Rekomendasi**: Masyarakat, pendaki, dan wisatawan tidak diperbolehkan mendekati kawah dalam radius bahaya yang ditetapkan PVMBG (biasanya radius 1 hingga 3 km dari kawah aktif)."
        ),
    },
    {
        "id": "status_level_3",
        "title": "Karakteristik & Arti Status Level III (Siaga) PVMBG",
        "matches": lambda q: bool(
            re.search(r"\b(level\s+(?:iii|3)|siaga)\b", q.lower())
            and re.search(r"\b(arti|maksud|definisi|pengertian|apa\s+itu|jelaskan|kriteria)\b", q.lower())
        ),
        "content": (
            "**Arti dan Karakteristik Status Level III (Siaga)** menurut standar PVMBG - Badan Geologi:\n\n"
            "1. **Arti**: Terjadi peningkatan aktivitas visual dan seismik secara nyata dan signifikan. Fluks gas dan deformasi mengindikasikan letusan berpeluang besar terjadi atau erupsi awal sedang berlangsung.\n"
            "2. **Potensi Bahaya**: Bahaya mengancam Kawasan Rawan Bencana (KRB) II, dapat berupa lontaran material pijar luas, abu vulkanik pekat, dan potensi awan panas guguran.\n"
            "3. **Tindakan & Rekomendasi**: Jalur pendakian ditutup total, masyarakat di kawasan rawan bencana menyiapkan barang berharga dan bersiap untuk evakuasi jika status dinaikkan."
        ),
    },
    {
        "id": "status_level_4",
        "title": "Karakteristik & Arti Status Level IV (Awas) PVMBG",
        "matches": lambda q: bool(
            re.search(r"\b(level\s+(?:iv|4)|awas)\b", q.lower())
            and re.search(r"\b(arti|maksud|definisi|pengertian|apa\s+itu|jelaskan|kriteria)\b", q.lower())
        ),
        "content": (
            "**Arti dan Karakteristik Status Level IV (Awas)** menurut standar PVMBG - Badan Geologi:\n\n"
            "1. **Arti**: Merupakan tingkatan tertinggi dalam sistem peringatan dini gunung api di Indonesia. Erupsi eksplosif utama sedang berlangsung atau akan segera terjadi dalam waktu dekat.\n"
            "2. **Potensi Bahaya**: Mengancam keselamatan jiwa penduduk di Kawasan Rawan Bencana (KRB) I, II, dan III berupa awan panas mematikan, lontaran batu besar, aliran piroklastik, dan banjir lahar hujan.\n"
            "3. **Tindakan & Rekomendasi**: Evakuasi segera bagi seluruh warga dalam radius rekomendasi (biasanya 5 hingga 10 km) ke pos pengungsian yang ditentukan pemerintah daerah/BPBD."
        ),
    },
    {
        "id": "status_level_1",
        "title": "Karakteristik & Arti Status Level I (Normal) PVMBG",
        "matches": lambda q: bool(
            re.search(r"\b(level\s+(?:i|1)|normal)\b", q.lower())
            and re.search(r"\b(arti|maksud|definisi|pengertian|apa\s+itu|jelaskan|kriteria)\b", q.lower())
        ),
        "content": (
            "**Arti dan Karakteristik Status Level I (Normal)** menurut standar PVMBG - Badan Geologi:\n\n"
            "1. **Arti**: Gunung api berada dalam keadaan dasar (istirahat/baseline), tidak menunjukkan tanda peningkatan aktivitas magma atau kegempaan.\n"
            "2. **Potensi Bahaya**: Minim sekali, bahaya yang mungkin timbul terbatas pada konsentrasi gas vulkanik di dasar kawah aktif.\n"
            "3. **Tindakan & Rekomendasi**: Masyarakat dan wisatawan dapat beraktivitas secara normal, namun tetap mematuhi aturan tidak menuruni kawah aktif."
        ),
    },
    {
        "id": "mitigasi_gerakan_tanah",
        "title": "Panduan Mitigasi Bencana Gerakan Tanah & Tanah Longsor (PVMBG - Badan Geologi)",
        "matches": lambda q: bool(
            re.search(r"\b(gerak(?:an)?\s*tanah|longsor|tanah\s*longsor|amblas(?:an)?|landslide)\b", q.lower())
            and re.search(r"\b(mitigasi|panduan|keselamatan|langkah|antisipasi|tindakan|pencegahan|cara\s+mencegah|apa\s+yang\s+harus\s+dilakukan|edukasi|tanda|gejala)\b", q.lower())
        ),
        "content": (
            "**Panduan Lengkap Mitigasi Bencana Gerakan Tanah & Tanah Longsor (PVMBG - Badan Geologi, Kementerian ESDM)**:\n\n"
            "1. **Kesiapsiagaan & Pencegahan (Pra-Bencana)**:\n"
            "- **Kenali Gejala & Tanda Awal**: Munculnya retakan tanah baru melengkung/memanjang pada lereng, jalan, atau dinding/lantai bangunan; tiang listrik atau pohon miring; pintu/jendela mendadak sulit dibuka; air sumur tiba-tiba keruh berlumpur atau ada rembesan air baru pada lereng; dan suara gemuruh dari arah tebing.\n"
            "- **Tindakan Penataan Lingkungan**: Hindari mendirikan bangunan hunian di lereng curam atau di sempadan alur longsor; buat saluran drainase kedap air yang lancar agar air hujan tidak meresap menjenuhkan lereng; jangan memotong lereng tegak lurus tanpa dinding penahan (retaining wall); serta tanam pohon berakar dalam (akar wangi/vetiver, bambu, aren) pada tebing rawan.\n\n"
            "2. **Tindakan Saat Terjadi Longsor (Tanggap Darurat)**:\n"
            "- Segera evakuasi menjauhi lereng atau lembah jalur aliran longsor menuju tempat terbuka yang datar dan stabil.\n"
            "- Bunyikan tanda bahaya (sirine/kentongan) untuk memperingatkan warga sekitar jika memungkinkan.\n"
            "- Jangan mendekati tebing atau material runtuhan longsor karena sangat berisiko terjadi longsor susulan.\n"
            "- Jika terjebak di dalam bangunan, lindungi kepala dan meringkuk di bawah perabot yang kokoh.\n\n"
            "3. **Tindakan Pasca-Bencana**:\n"
            "- Waspadai longsor susulan terutama saat hujan deras masih terus turun.\n"
            "- Jangan langsung memasuki rumah yang terdampak retakan sebelum diperiksa oleh tim tanggap darurat Badan Geologi atau BPBD.\n"
            "- Periksa instalasi listrik dan gas guna menghindari bahaya kebakaran sekunder.\n"
            "- Pantau terus informasi resmi dan laporan penyelidikan dari Badan Geologi (PVMBG) dan BPBD setempat."
        ),
    },
    {
        "id": "mitigasi_erupsi_gunungapi",
        "title": "Panduan Mitigasi Bencana Erupsi Gunung Api (PVMBG - Badan Geologi)",
        "matches": lambda q: bool(
            re.search(r"\b(erupsi|letusan|gunung\s+api|vulkanik)\b", q.lower())
            and re.search(r"\b(mitigasi|panduan|keselamatan|langkah|antisipasi|tindakan|pencegahan|apa\s+yang\s+harus\s+dilakukan|edukasi)\b", q.lower())
        ),
        "content": (
            "**Panduan Mitigasi & Keselamatan Bencana Erupsi Gunung Api (PVMBG - Badan Geologi, Kementerian ESDM)**:\n\n"
            "1. **Pra-Bencana (Kesiapsiagaan)**:\n"
            "- Kenali tingkat status aktivitas gunung api terdekat (Normal, Waspada, Siaga, Awas) dan peta Kawasan Rawan Bencana (KRB).\n"
            "- Siapkan Tas Siaga Bencana (dokumen penting, obat-obatan, senter, makanan siap saji, air minum).\n"
            "- Siapkan masker pelindung pernapasan dan kacamata (*goggles*) untuk mengantisipasi paparan abu vulkanik.\n"
            "- Ketahui jalur evakuasi dan lokasi titik kumpul aman yang telah ditentukan oleh BPBD dan pemerintah setempat.\n\n"
            "2. **Saat Terjadi Erupsi (Tanggap Darurat)**:\n"
            "- Segera jauhi zona bahaya dan radius rekomendasi yang telah ditetapkan oleh PVMBG.\n"
            "- Hindari area lembah sungai yang berhulu di puncak gunung guna menghindari ancaman awan panas guguran dan aliran lahar.\n"
            "- Lindungi diri dari hujan abu: gunakan masker basah atau masker debu, kenakan pakaian tertutup, topi, dan kacamata.\n"
            "- Berlindung di dalam bangunan beratap kokoh dan tutup seluruh pintu serta ventilasi jendela saat terjadi hujan abu lebat.\n\n"
            "3. **Pasca-Erupsi**:\n"
            "- Waspadai bahaya sekunder berupa lahar hujan di sepanjang aliran sungai saat turun hujan di area puncak.\n"
            "- Bersihkan timbunan abu vulkanik dari atap rumah agar struktur atap tidak runtuh akibat beban berat abu.\n"
            "- Ikuti instruksi resmi pos pengamatan gunung api PVMBG dan otoritas penanggulangan bencana daerah (BPBD)."
        ),
    },
]


class KnowledgeBaseTool:
    """Tool for querying authoritative official PVMBG standards, alert levels, and geological guidance.
    NOTE: In the API Documentation pipeline, this tool provides official PVMBG standard definitions.
    It NEVER queries the vector database or document_chunks table, ensuring strict separation
    between API Documentation and Knowledge Base."""

    @staticmethod
    def execute(query: str, top_k: int = 3) -> Dict[str, Any]:
        # 1. Check authoritative official PVMBG knowledge first for conceptual/level queries
        matched_doc = None
        for doc in OFFICIAL_PVMBG_KNOWLEDGE_DOCS:
            if doc["matches"](query):
                matched_doc = doc
                break

        if matched_doc:
            return {
                "status": "success",
                "output": f"Informasi Resmi Standar PVMBG - Badan Geologi ({matched_doc['title']}):\n\n{matched_doc['content']}",
                "references": [],
                "raw_results": [],
                "intent": "KNOWLEDGE_BASE",
                "api_call": resolve_api_url("/api/v2/gunung-api/tingkat-aktivitas"),
            }

        # 2. If user specifically asks for uploaded documents, PDFs, or files while in API mode:
        if re.search(r"\b(dokumen|file|pdf|skripsi|laporan\s+kerja|proposal|halaman|bab|arsip|upload|unduh|buletin)\b", query, re.IGNORECASE):
            redirect_msg = (
                "ℹ️ **Informasi Pemisahan Layanan**:\n"
                "Untuk mencari informasi, membaca kutipan, atau menganalisis file dokumen internal (seperti file PDF, buletin, dan laporan kerja yang diunggah), "
                "silakan beralih ke menu **Knowledge Base** pada tab di bagian atas layar.\n\n"
                "Tab **API Documentation** ini khusus melayani akses data resmi langsung dari API MAGMA Indonesia (status aktivitas gunung api real-time, laporan kejadian gempa bumi, tanggap darurat gerakan tanah, dan rekomendasi keselamatan geologi)."
            )
            return {
                "status": "success",
                "output": redirect_msg,
                "references": [],
                "raw_results": [],
                "intent": "KNOWLEDGE_BASE",
                "api_call": None,
            }

        return {
            "status": "not_found",
            "output": "Informasi standar resmi untuk istilah tersebut belum tercatat di sistem API MAGMA Indonesia. Untuk mencari dokumen atau buletin internal, silakan gunakan tab menu **Knowledge Base** di atas.",
            "references": [],
            "raw_results": [],
            "intent": "KNOWLEDGE_BASE",
            "api_call": None,
        }


def is_truncated_response(text: str) -> bool:
    """Detect if an LLM-generated response was abruptly truncated mid-sentence or mid-token."""
    if not text or not text.strip():
        return True
    stripped = text.strip()

    # 1. Ends with unclosed markdown tags
    if stripped.endswith("**") or stripped.endswith("*") or stripped.endswith("__") or stripped.endswith("`"):
        return True
    if stripped.count("**") % 2 != 0:
        return True

    # 2. Ends with trailing colon, dash, comma, or ellipsis
    if stripped.endswith(":") or stripped.endswith("-") or stripped.endswith(",") or stripped.endswith("..."):
        return True

    # 3. Ends with incomplete table markup
    if stripped.endswith("|") or stripped.endswith("|-") or stripped.endswith("| *"):
        return True

    # 4. Ends with Indonesian conjunctions, prepositions, or linking verbs
    words = re.findall(r"\b\w+\b", stripped.lower())
    if words:
        last_word = words[-1]
        hanging_words = {
            "dan", "atau", "pada", "yang", "di", "ke", "dari", "adalah", "yaitu", 
            "merupakan", "berada", "sebesar", "dengan", "untuk", "seperti", "status",
            "level", "rekomendasi", "rekomendasinya", "karena", "agar", "supaya",
            "bahwa", "serta", "tetapi", "namun", "juga"
        }
        if last_word in hanging_words:
            return True

    # 5. Check if the string ends with a standard sentence-closing character
    last_char = stripped[-1]
    if last_char not in {".", "!", "?", '"', "'", ")", "]", "}", "\n"}:
        return True

    return False


class AnswerGenerator:
    """Grounds validated tool outputs and synthesizes conversational AI responses using model_chat."""

    @staticmethod
    def generate(
        user_input: str,
        tool_output: str,
        tool_name: str,
        history: str = "",
        entity: Optional[str] = None,
        lang: str = "id",
    ) -> str:
        if not tool_output or not tool_output.strip():
            return "Data dari layanan resmi MAGMA Indonesia belum tersedia untuk permintaan tersebut saat ini."

        # If tool_output indicates missing data, return directly
        if "tidak ditemukan" in tool_output.lower() and len(tool_output.split("\n")) <= 2:
            return tool_output

        # If official document content or pre-formatted table is already authoritative, return directly
        if tool_output.startswith("Informasi Resmi Standar PVMBG") or tool_output.startswith("📋 Panduan"):
            return tool_output

        system_prompt = (
            "Anda adalah AI Assistant profesional resmi MAGMA Indonesia (Pusat Vulkanologi dan Mitigasi Bencana Geologi - PVMBG, Badan Geologi, Kementerian ESDM).\n"
            "TUGAS:\n"
            "Jawab pertanyaan pengguna secara informatif, alami, jelas, dan profesional dalam Bahasa Indonesia (atau Bahasa Inggris jika pertanyaan dalam bahasa Inggris).\n"
            "ATURAN KETAT:\n"
            "1. Jawab HANYA berdasarkan DATA RESMI yang diberikan. JANGAN PERNAH mengarang data, angka, lokasi, atau status yang tidak ada.\n"
            "2. Pertahankan akurasi angka, nama gunung/wilayah, tanggal, dan tingkat aktivitas persis seperti data resmi.\n"
            "3. JANGAN mengulang salam pembuka yang panjang (seperti 'Halo saya MAGMA...') jika percakapan sudah berlangsung.\n"
            "4. Sajikan jawaban yang mudah dipahami masyarakat umum dengan format teks/markdown yang rapi (bullet points jika perlu rincian)."
        )

        user_prompt = (
            f"Pertanyaan Pengguna: {user_input}\n"
            + (f"Entitas/Topik yang dibahas: {entity}\n" if entity else "")
            + f"\nDATA RESMI DARI SISTEM / TOOL ({tool_name}):\n{tool_output}\n\n"
            "Sintesiskan data resmi di atas menjadi jawaban yang ramah, profesional, dan to-the-point sesuai pertanyaan pengguna."
        )

        try:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            ai_answer = model_chat(messages, temperature=0.2, max_tokens=1500)
            if ai_answer and len(ai_answer.strip()) > 20:
                rejected_sub = (
                    "trouble connecting", "oops", "error", "rate limit", 
                    "terjadi kesalahan", "maaf, saya tidak", "tidak dapat memproses"
                )
                if any(r in ai_answer.lower() for r in rejected_sub):
                    logger.warning(f"[ANSWER_GENERATOR] LLM returned error phrase: '{ai_answer}'. Falling back to tool_output.")
                    return tool_output

                if not is_truncated_response(ai_answer):
                    return ai_answer.strip()
                logger.warning(f"[ANSWER_GENERATOR] LLM generated truncated response: '{ai_answer[-30:]}'. Falling back to complete tool_output.")
                return tool_output
        except Exception as e:
            logger.warning(f"[ANSWER_GENERATOR] LLM generation failed or timed out: {e}. Falling back to tool output.")

        return tool_output


def extract_active_entity_from_history(history: str, volcano_resp: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """Extract the active volcano entity (code, name) from conversation memory."""
    if not history:
        return None, None
    lines = history.strip().split("\n")

    # 1. Prioritize USER questions in reverse order (what volcano was the user actively talking about?)
    for line in reversed(lines):
        if line.startswith("user:"):
            q_text = line[5:].strip()
            # Skip pure conceptual/knowledge questions
            if re.search(r"\b(arti|tingkat|level|definisi|pengertian)\b", q_text.lower()) and not re.search(r"\bgunung\s+[a-z]", q_text.lower()):
                continue
            detected = _detect_volcano_name(q_text, volcano_resp) if volcano_resp else None
            if detected:
                code = detected[0]
                matched = next((v for v in volcano_resp if (v.get("ga_code") or "").upper() == code.upper()), None)
                if matched:
                    return code, matched.get("ga_nama_gapi")

    # 2. Check assistant lines for explicit "Gunung <Name>" statements
    for line in reversed(lines):
        m = re.search(r"(?:Gunung|Mount|G\.)\s+([A-Z][a-zA-Z\s\-]+?)(?:\s*,|\s*\(|\s*\?|\.|\s+adalah|\s+berstatus|\s+berjarak|$)", line)
        if m:
            cand = m.group(1).strip()
            if cand.lower() not in {"api", "berapi", "terdekat", "aktif", "ini", "lewat"}:
                matched = next((v for v in volcano_resp if cand.lower() == (v.get("ga_nama_gapi") or "").lower()), None)
                if matched:
                    return matched.get("ga_code"), matched.get("ga_nama_gapi")

    return None, None


# ---------------------------------------------------------------------------
# 2. DYNAMIC FOLLOW-UP GENERATOR
# (LLM + Conversation Memory + Intent + Source Context + Structured Output)
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS_SPEC = [
    {
        "intent": "volcano_status",
        "description": "Cek tingkat status (Level I Normal, Level II Waspada, Level III Siaga, Level IV Awas) dan rekomendasi resmi PVMBG untuk gunung api tertentu.",
        "requires_entity": True,
        "sample_action": "Bagaimana status Gunung {entity}?",
    },
    {
        "intent": "volcano_recommendation",
        "description": "Cek rincian rekomendasi keselamatan PVMBG untuk warga / wisatawan terkait gunung api tertentu.",
        "requires_entity": True,
        "sample_action": "Bagaimana rekomendasi PVMBG untuk Gunung {entity}?",
    },
    {
        "intent": "volcano_eruption_history",
        "description": "Cek riwayat catatan erupsi / letusan terbaru gunung api tertentu dari VEN API.",
        "requires_entity": True,
        "sample_action": "Erupsi terakhir Gunung {entity}",
    },
    {
        "intent": "volcano_active_list",
        "description": "Lihat daftar seluruh gunung api di Indonesia yang saat ini berstatus aktif di atas Normal (Level II Waspada, Level III Siaga, Level IV Awas).",
        "requires_entity": False,
        "sample_action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
    },
    {
        "intent": "location_safety",
        "description": "Cek gunung api terdekat atau potensi bahaya geologi di sekitar lokasi koordinat pengguna.",
        "requires_entity": False,
        "sample_action": "Gunung apa yang paling dekat dengan saya?",
    },
    {
        "intent": "earthquake_list",
        "description": "Lihat daftar kejadian gempa bumi terkini atau gempa signifikan yang tercatat di Indonesia.",
        "requires_entity": False,
        "sample_action": "Daftar kejadian gempa bumi terkini",
    },
    {
        "intent": "earthquake_mitigation",
        "description": "Lihat panduan langkah mitigasi dan keselamatan saat serta setelah terjadi gempa bumi / tsunami.",
        "requires_entity": False,
        "sample_action": "Bagaimana panduan mitigasi bencana gempa bumi?",
    },
    {
        "intent": "ground_movement_list",
        "description": "Lihat laporan kejadian gerakan tanah atau tanah longsor terkini.",
        "requires_entity": False,
        "sample_action": "Laporan kejadian gerakan tanah terbaru",
    },
    {
        "intent": "ground_movement_mitigation",
        "description": "Lihat panduan lengkap langkah mitigasi, ciri-ciri bahaya, dan keselamatan bencana gerakan tanah serta tanah longsor.",
        "requires_entity": False,
        "sample_action": "Bagaimana panduan mitigasi bencana gerakan tanah dan longsor?",
    },
    {
        "intent": "knowledge_base",
        "description": "Informasi standar resmi PVMBG mengenai 4 tingkatan status gunung api, pedoman mitigasi bencana, dan istilah vulkanologi/geologi.",
        "requires_entity": False,
        "sample_action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
    },
    {
        "intent": "volcano_status_level_explanation",
        "description": "Penjelasan arti dan kriteria 4 tingkatan status aktivitas gunung api (Level I Normal, Level II Waspada, Level III Siaga, Level IV Awas).",
        "requires_entity": False,
        "sample_action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
    },
]


def extract_executed_actions(history: str, current_query: str) -> List[str]:
    """Extract list of user queries and actions already executed in this conversation."""
    actions = []
    if history:
        for line in history.split("\n"):
            line_s = line.strip()
            if line_s.startswith("user:"):
                q = line_s[len("user:"):].strip()
                if q and q.lower() not in {"ya", "iya", "yaa", "boleh", "ok", "oke", "lanjut", "tidak", "gak", "nggak"}:
                    if q not in actions:
                        actions.append(q)
    if current_query and current_query.lower() not in {"ya", "iya", "yaa", "boleh", "ok", "oke", "lanjut", "tidak", "gak", "nggak"}:
        if current_query not in actions:
            actions.append(current_query)
    return actions


def _is_similar_action(act1: str, act2: str) -> bool:
    """Check if two actions or queries are identical or semantically duplicate."""
    if not act1 or not act2:
        return False
    a1 = re.sub(r"[^a-zA-Z0-9\s]", "", act1.lower()).strip()
    a2 = re.sub(r"[^a-zA-Z0-9\s]", "", act2.lower()).strip()
    if a1 == a2 or a1 in a2 or a2 in a1:
        return True
    w1 = set(a1.split())
    w2 = set(a2.split())
    common = w1 & w2
    if len(common) >= 3 and (len(common) / max(len(w1), len(w2))) > 0.6:
        return True
    return False


class FollowUpGenerator:
    """Dynamically generates 2-3 structured, contextual follow-up questions using model_chat()."""

    @staticmethod
    def generate(
        conversation_history: str,
        current_query: str,
        current_intent: str,
        current_entity: Optional[str],
        assistant_answer: str,
        tool_results: Any,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        executed_actions: Optional[List[str]] = None,
        lang: str = "id",
    ) -> List[Dict[str, Any]]:
        tools = available_tools or AVAILABLE_TOOLS_SPEC
        if executed_actions is None:
            executed_actions = extract_executed_actions(conversation_history, current_query)

        # If specific entity is being discussed, use grounded entity-aware candidates directly
        # to prevent small LLMs from generating unroutable or awkward questions.
        if current_entity:
            return FollowUpGenerator._contextual_fallback(
                current_intent=current_intent,
                current_entity=current_entity,
                executed_actions=executed_actions,
                current_query=current_query,
                lang=lang,
            )

        # 1. Build prompt for model_chat()
        valid_intents = [t['intent'] for t in tools]

        system_prompt = (
            "Anda adalah AI Asisten MAGMA Indonesia (PVMBG, Badan Geologi, Kementerian ESDM).\n"
            "Tugas: Buat 2-3 opsi follow-up (pertanyaan lanjutan) yang relevan dan kontekstual.\n"
            "Aturan:\n"
            "1. Jika ada nama gunung yang sedang dibahas, pertahankan nama gunung tersebut di label/action.\n"
            "2. Jangan ulangi hal yang sudah pernah ditanyakan di executed_actions.\n"
            f"3. Pilihan intent yang valid: {', '.join(valid_intents)}.\n"
            "4. Format HANYA JSON persis: {\"follow_ups\": [{\"id\": \"fu_1\", \"label\": \"...\", \"intent\": \"...\", \"entity\": \"...\", \"action\": \"...\"}]}"
        )

        user_prompt = (
            f"Query Pengguna: {current_query}\n"
            f"Intent: {current_intent} | Entitas: {current_entity or 'Tidak ada'}\n"
            f"Ringkasan Jawaban: {assistant_answer[:250]}\n"
            f"Sudah Dijalankan: {json.dumps(executed_actions[-3:], ensure_ascii=False) if executed_actions else '[]'}\n\n"
            "Buat 2-3 follow-up JSON:"
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

        # 2. Invoke model_chat() with strict grounding & parsing
        try:
            raw_response = model_chat(messages, temperature=0.1, max_tokens=350)
            if raw_response:
                clean_json = raw_response.strip()
                if "```" in clean_json:
                    clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                    clean_json = re.sub(r"\s*```$", "", clean_json)
                start_i = clean_json.find("{")
                end_i = clean_json.rfind("}")
                if start_i != -1 and end_i != -1:
                    clean_json = clean_json[start_i:end_i+1]
                data = json.loads(clean_json)
                raw_items = data.get("follow_ups", [])
                valid_items = []
                for item in raw_items:
                    if not isinstance(item, dict):
                        continue
                    label = (item.get("label") or "").strip()
                    action = (item.get("action") or "").strip()
                    intent_val = (item.get("intent") or "").strip().lower()
                    entity_val = item.get("entity") or current_entity
                    item_id = item.get("id") or f"fu_{len(valid_items)+1}"

                    CANONICAL_INTENT_DATA = {
                        "volcano_recommendation": ("Lihat rekomendasi masyarakat", f"Bagaimana rekomendasi PVMBG untuk Gunung {current_entity or 'ini'}?"),
                        "volcano_status": ("Cek status aktivitas", f"Bagaimana status Gunung {current_entity or 'ini'}?"),
                        "volcano_eruption_history": ("Lihat riwayat erupsi", f"Kapan erupsi terakhir Gunung {current_entity or 'ini'}?"),
                        "volcano_active_list": ("Lihat gunung api aktif di atas Normal", "Gunung apa saja yang berstatus waspada, siaga, atau awas?"),
                        "volcano_status_level_explanation": ("Arti tingkatan status gunung api", "Jelaskan arti tingkatan status gunung api dari normal hingga awas"),
                        "location_safety": ("Cek gunung api terdekat", "Gunung apa yang paling dekat dengan saya?"),
                        "earthquake_list": ("Daftar gempa bumi terkini", "Daftar kejadian gempa bumi terkini"),
                        "earthquake_mitigation": ("Panduan mitigasi gempa", "Bagaimana panduan mitigasi bencana gempa bumi?"),
                        "ground_movement_list": ("Laporan gerakan tanah terbaru", "Laporan kejadian gerakan tanah terbaru"),
                        "ground_movement_mitigation": ("Panduan mitigasi tanah longsor", "Bagaimana panduan mitigasi bencana gerakan tanah dan longsor?"),
                        "knowledge_base": ("Panduan mitigasi bencana", "Bagaimana panduan mitigasi bencana erupsi gunung api?"),
                    }
                    if action in CANONICAL_INTENT_DATA:
                        c_lbl, c_act = CANONICAL_INTENT_DATA[action]
                        action = c_act
                        if not label or label in CANONICAL_INTENT_DATA or "_" in label:
                            label = c_lbl
                    elif label in CANONICAL_INTENT_DATA:
                        label = CANONICAL_INTENT_DATA[label][0]

                    # Clean placeholder labels from LLM
                    if "teks label" in label.lower() or "string_id" in label.lower() or "_" in label or not label:
                        label = action[:35] if len(action) <= 35 else action[:32] + "..."

                    if not action:
                        continue

                    # Filter duplicates against executed_actions and current_query
                    if any(_is_similar_action(action, act) for act in executed_actions):
                        continue
                    if _is_similar_action(action, current_query):
                        continue

                    # Preserve entity in action text if volcano-specific
                    if current_entity and current_entity.lower() not in action.lower() and intent_val in {"volcano_status", "volcano_recommendation", "volcano_eruption_history"}:
                        action = f"{action} Gunung {current_entity}"
                        entity_val = current_entity

                    valid_items.append({
                        "id": f"fu_{len(valid_items)+1}",
                        "label": label[:60],
                        "intent": intent_val,
                        "entity": entity_val,
                        "action": action,
                        "query": action,  # backward compatibility
                    })
                    if len(valid_items) >= 3:
                        break

                if valid_items:
                    return valid_items
        except Exception as e:
            logger.warning(f"[FollowUpGenerator] Dynamic LLM generation error: {e}. Falling back to contextual validator.")

        # 3. Contextual Fallback Generator (Anti-Loop, Grounded)
        return FollowUpGenerator._contextual_fallback(
            current_intent=current_intent,
            current_entity=current_entity,
            executed_actions=executed_actions,
            current_query=current_query,
            lang=lang,
        )

    @staticmethod
    def _contextual_fallback(
        current_intent: str,
        current_entity: Optional[str],
        executed_actions: List[str],
        current_query: str,
        lang: str = "id",
    ) -> List[Dict[str, Any]]:
        """Contextual fallback generator if LLM times out or returns malformed JSON."""
        candidates = []
        c_intent = (current_intent or "").upper()

        if current_entity:
            candidates.append({
                "id": "volcano_recommendation",
                "label": f"Lihat rekomendasi untuk masyarakat",
                "intent": "volcano_recommendation",
                "entity": current_entity,
                "action": f"Bagaimana rekomendasi PVMBG untuk Gunung {current_entity}?",
            })
            candidates.append({
                "id": "volcano_eruption_history",
                "label": f"Lihat riwayat erupsi",
                "intent": "volcano_eruption_history",
                "entity": current_entity,
                "action": f"Erupsi terakhir Gunung {current_entity}",
            })
            candidates.append({
                "id": "volcano_status",
                "label": f"Cek status aktivitas",
                "intent": "volcano_status",
                "entity": current_entity,
                "action": f"Bagaimana status Gunung {current_entity}?",
            })
            candidates.append({
                "id": "volcano_active_list",
                "label": "Daftar gunung api aktif lainnya",
                "intent": "volcano_active_list",
                "entity": None,
                "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            })
        elif "KNOWLEDGE" in c_intent or "EXPLANATION" in c_intent:
            candidates.append({
                "id": "volcano_active_list",
                "label": "Lihat gunung api aktif di atas Normal",
                "intent": "volcano_active_list",
                "entity": None,
                "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            })
            candidates.append({
                "id": "location_safety",
                "label": "Cek gunung api terdekat dari lokasi",
                "intent": "location_safety",
                "entity": None,
                "action": "Gunung apa yang paling dekat dengan saya?",
            })
            candidates.append({
                "id": "knowledge_base",
                "label": "Panduan mitigasi erupsi gunung api",
                "intent": "knowledge_base",
                "entity": None,
                "action": "Bagaimana panduan mitigasi bencana erupsi gunung api?",
            })
        elif c_intent == "VOLCANO_ACTIVE_LIST":
            candidates.append({
                "id": "location_safety",
                "label": "Cek gunung api terdekat",
                "intent": "location_safety",
                "entity": None,
                "action": "Gunung apa yang paling dekat dengan saya?",
            })
            candidates.append({
                "id": "knowledge_base",
                "label": "Pelajari arti tingkatan status",
                "intent": "knowledge_base",
                "entity": None,
                "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
            })
        elif "EARTHQUAKE" in c_intent:
            if "MITIGATION" in c_intent:
                candidates.append({
                    "id": "earthquake_list",
                    "label": "Daftar gempa bumi terkini",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                })
                candidates.append({
                    "id": "ground_movement_list",
                    "label": "Laporan gerakan tanah terbaru",
                    "intent": "ground_movement_list",
                    "entity": None,
                    "action": "Laporan kejadian gerakan tanah terbaru",
                })
            else:
                candidates.append({
                    "id": "earthquake_mitigation",
                    "label": "Panduan mitigasi gempa",
                    "intent": "earthquake_mitigation",
                    "entity": None,
                    "action": "Bagaimana panduan mitigasi bencana gempa bumi?",
                })
                candidates.append({
                    "id": "ground_movement_list",
                    "label": "Laporan gerakan tanah terbaru",
                    "intent": "ground_movement_list",
                    "entity": None,
                    "action": "Laporan kejadian gerakan tanah terbaru",
                })
        elif "GROUND_MOVEMENT" in c_intent:
            if "MITIGATION" in c_intent:
                candidates.append({
                    "id": "ground_movement_list",
                    "label": "Laporan gerakan tanah terbaru",
                    "intent": "ground_movement_list",
                    "entity": None,
                    "action": "Laporan kejadian gerakan tanah terbaru",
                })
                candidates.append({
                    "id": "earthquake_mitigation",
                    "label": "Panduan mitigasi gempa bumi",
                    "intent": "earthquake_mitigation",
                    "entity": None,
                    "action": "Bagaimana panduan mitigasi bencana gempa bumi?",
                })
            else:
                candidates.append({
                    "id": "ground_movement_mitigation",
                    "label": "Panduan mitigasi tanah longsor",
                    "intent": "ground_movement_mitigation",
                    "entity": None,
                    "action": "Bagaimana panduan mitigasi bencana gerakan tanah dan longsor?",
                })
                candidates.append({
                    "id": "earthquake_list",
                    "label": "Daftar gempa bumi terkini",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                })
        elif "LOCATION" in c_intent:
            candidates.append({
                "id": "volcano_active_list",
                "label": "Lihat gunung api aktif di atas Normal",
                "intent": "volcano_active_list",
                "entity": None,
                "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            })
            candidates.append({
                "id": "knowledge_base",
                "label": "Pelajari arti tingkatan status",
                "intent": "knowledge_base",
                "entity": None,
                "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
            })

        if not candidates:
            candidates.append({
                "id": "volcano_active_list",
                "label": "Lihat gunung api aktif di atas Normal",
                "intent": "volcano_active_list",
                "entity": None,
                "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            })
            candidates.append({
                "id": "location_safety",
                "label": "Cek gunung api terdekat",
                "intent": "location_safety",
                "entity": None,
                "action": "Gunung apa yang paling dekat dengan saya?",
            })
            candidates.append({
                "id": "knowledge_base",
                "label": "Pelajari arti tingkatan status",
                "intent": "knowledge_base",
                "entity": None,
                "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
            })

        valid = []
        for cand in candidates:
            act = cand["action"]
            if any(_is_similar_action(act, past) for past in executed_actions):
                continue
            if _is_similar_action(act, current_query):
                continue
            cand["query"] = act
            valid.append(cand)
            if len(valid) >= 3:
                break
        return valid


# ---------------------------------------------------------------------------
# 3. AI AGENT ROUTER (DECISION ENGINE)
# ---------------------------------------------------------------------------

class AgentRouter:
    """Central AI Agent Router that routes user input to the correct tool with validation.
    
    Principles:
    1. CURRENT QUERY FIRST: The current user query determines the intent and tool.
    2. KB / RAG PRIORITY: Conceptual & status level questions route to KB/RAG, never to volcano status API.
    3. CONTEXTUAL REFINEMENT: Previous history is used solely for:
       - entity continuity on anaphora ("gunung tersebut", "-nya", "rekomendasinya")
       - pronoun resolution
       - short confirmation resolution against pending_action
    """

    @staticmethod
    def route_and_execute(
        user_input: str,
        geo_location: Optional[Tuple[float, float]],
        history: str = "",
        location_name: Optional[str] = None,
        location_accuracy: Optional[float] = None,
        lang: str = "id",
    ) -> Dict[str, Any]:
        text_lower = user_input.lower().strip()
        has_geo = bool(geo_location and any(geo_location))
        executed_actions = extract_executed_actions(history, user_input)

        # Load volcano list / cache
        volcano_resp = get_mount_code() or load_volcano_cache() or []

        # ===================================================================
        # STAGE -1: RESOLVE RAW INTENT ACTION KEYS FROM BUTTON CLICKS
        # (e.g. if follow-up chip sent raw identifier like volcano_recommendation)
        # ===================================================================
        clean_raw_q = re.sub(r"[^\w]", "", text_lower)
        RAW_INTENT_KEY_MAP = {
            "volcano_recommendation": "Bagaimana rekomendasi PVMBG untuk {entity}?",
            "volcanorecommendation": "Bagaimana rekomendasi PVMBG untuk {entity}?",
            "volcano_status": "Bagaimana status Gunung {entity}?",
            "volcanostatus": "Bagaimana status Gunung {entity}?",
            "volcano_eruption_history": "Kapan erupsi terakhir Gunung {entity}?",
            "volcanoeruptionhistory": "Kapan erupsi terakhir Gunung {entity}?",
            "volcano_active_list": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            "volcanoactivelist": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
            "volcano_status_level_explanation": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
            "volcanostatuslevelexplanation": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
            "location_safety": "Gunung apa yang paling dekat dengan saya?",
            "locationsafety": "Gunung apa yang paling dekat dengan saya?",
            "earthquake_list": "Daftar kejadian gempa bumi terkini",
            "earthquakelist": "Daftar kejadian gempa bumi terkini",
            "earthquake_mitigation": "Bagaimana panduan mitigasi bencana gempa bumi?",
            "earthquakemitigation": "Bagaimana panduan mitigasi bencana gempa bumi?",
            "ground_movement_list": "Laporan kejadian gerakan tanah terbaru",
            "groundmovementlist": "Laporan kejadian gerakan tanah terbaru",
            "ground_movement_mitigation": "Bagaimana panduan mitigasi bencana gerakan tanah dan longsor?",
            "groundmovementmitigation": "Bagaimana panduan mitigasi bencana gerakan tanah dan longsor?",
            "knowledge_base": "Bagaimana panduan mitigasi bencana erupsi gunung api?",
            "knowledgebase": "Bagaimana panduan mitigasi bencana erupsi gunung api?",
        }
        if clean_raw_q in RAW_INTENT_KEY_MAP:
            matched_template = RAW_INTENT_KEY_MAP[clean_raw_q]
            hist_code, hist_name = extract_active_entity_from_history(history, volcano_resp) if (history and volcano_resp) else (None, None)
            if "{entity}" in matched_template:
                if hist_name:
                    user_input = matched_template.format(entity=hist_name)
                else:
                    user_input = "Bagaimana rekomendasi keselamatan untuk gunung api aktif di Indonesia saat ini?" if "rekomendasi" in matched_template else "Gunung apa saja yang berstatus waspada, siaga, atau awas?"
            else:
                user_input = matched_template
            text_lower = user_input.lower().strip()
            logger.info(f"[ROUTER] Automatically resolved raw intent key '{clean_raw_q}' to natural query: '{user_input}'")

        # ===================================================================
        # STAGE 0: GREETINGS & CAPABILITY / IDENTITY HANDLING
        # ===================================================================
        clean_q = re.sub(r"[^\w\s]", "", text_lower).strip()
        GREETING_WORDS = {
            "halo", "hai", "hi", "hey", "hallo", "assalamualaikum", "assalamualaikum wr wb",
            "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "p", "permisi",
            "tes", "test", "ping"
        }
        GRATITUDE_WORDS = {
            "terima kasih", "terimakasih", "makasih", "makasi", "makasih banyak", "terima kasih banyak",
            "thx", "thanks", "thank you", "sama sama", "samasama", "ok makasih", "oke makasih",
            "siap", "siap terima kasih", "baik terima kasih", "ok terima kasih", "oke terima kasih",
            "mantap", "sip", "ok sip", "oke sip", "makasih ya", "makasih yaa"
        }
        is_greeting = clean_q in GREETING_WORDS
        is_gratitude = (
            clean_q in GRATITUDE_WORDS
            or bool(re.search(r"\b(terima\s*kasih|makasih|matur\s*nuwun|hatur\s*nuhun|thanks|thank\s*you)\b", text_lower))
        ) and not bool(re.search(r"\b(gunung|gempa|tsunami|longsor|kawah|erupsi|pvmbg|magma)\b", text_lower))
        is_capability = bool(
            re.search(r"^\s*(siapa\s+kamu|kamu\s+siapa|apa\s+kamu|kamu\s+ini\s+apa|tentang\s+kamu)\s*$", clean_q)
            or re.search(r"^\s*(bisa\s+apa(?:\s+saja)?|apa\s+(?:saja\s+)?kemampuan(?:mu)?|fitur\s+apa(?:\s+saja)?|apa\s+fungsi(?:mu)?)\s*$", clean_q)
        )

        if is_gratitude:
            logger.info("[ROUTER] Intent: GRATITUDE")
            grat_text = (
                "Sama-sama! Senang bisa membantu Anda.\n\n"
                "Jika memerlukan pemantauan terbaru seputar aktivitas gunung api, gempa bumi, atau mitigasi bencana geologi lainnya di Indonesia, saya selalu siap membantu. Tetap waspada dan utamakan keselamatan! 🌋🛡️"
            )
            follow_ups = [
                {
                    "id": "fu_1",
                    "label": "Cek gunung api aktif di atas Normal",
                    "intent": "volcano_active_list",
                    "entity": None,
                    "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "query": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                },
                {
                    "id": "fu_2",
                    "label": "Info kejadian gempa bumi terkini",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                    "query": "Daftar kejadian gempa bumi terkini",
                },
                {
                    "id": "fu_3",
                    "label": "Penjelasan tingkatan status gunung api",
                    "intent": "volcano_status_level_explanation",
                    "entity": None,
                    "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                    "query": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                },
            ]
            return {
                "status": "success",
                "output": grat_text,
                "answer": grat_text,
                "api_call": None,
                "response": None,
                "references": None,
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": follow_ups[0]["action"],
                "intent": "GRATITUDE",
                "context": {
                    "intent": "GRATITUDE",
                    "entity": None,
                    "pending_action": follow_ups[0]["action"],
                    "executed_actions": executed_actions,
                },
            }

        if is_greeting:
            logger.info("[ROUTER] Intent: GREETING")
            if history:
                greet_text = "Halo! Ada yang bisa saya bantu terkait informasi status aktivitas gunung api, gempa bumi, atau bencana geologi saat ini?"
            else:
                greet_text = (
                    "Halo! Saya adalah **Asisten AI MAGMA Indonesia** resmi dari Badan Geologi (PVMBG) - Kementerian ESDM.\n\n"
                    "Saya siap membantu Anda memberikan informasi terkini seputar:\n"
                    "• 🌋 **Status Aktivitas Gunung Api** (Level I s/d Level IV) & rekomendasi jarak bahaya\n"
                    "• 🌐 **Laporan Gempa Bumi & Tsunami** terkini serta analisis geologis\n"
                    "• ⚠️ **Laporan Gerakan Tanah (Longsor)** & peta kerentanan\n"
                    "• 📍 **Pengecekan Ancaman Geologi Terdekat** dari koordinat lokasi Anda\n\n"
                    "Ada informasi yang ingin Anda ketahui seputar kebencanaan geologi saat ini?"
                )
            follow_ups = [
                {
                    "id": "fu_1",
                    "label": "Cek gunung api aktif di atas Normal",
                    "intent": "volcano_active_list",
                    "entity": None,
                    "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "query": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                },
                {
                    "id": "fu_2",
                    "label": "Info kejadian gempa bumi terkini",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                    "query": "Daftar kejadian gempa bumi terkini",
                },
                {
                    "id": "fu_3",
                    "label": "Penjelasan tingkatan status gunung api",
                    "intent": "volcano_status_level_explanation",
                    "entity": None,
                    "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                    "query": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                },
            ]
            return {
                "status": "success",
                "output": greet_text,
                "answer": greet_text,
                "api_call": None,
                "response": None,
                "references": None,
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": follow_ups[0]["action"],
                "intent": "GREETING",
                "context": {
                    "intent": "GREETING",
                    "entity": None,
                    "pending_action": follow_ups[0]["action"],
                    "executed_actions": executed_actions,
                },
            }

        if is_capability:
            logger.info("[ROUTER] Intent: CAPABILITY")
            cap_text = (
                "Saya adalah **Asisten AI MAGMA Indonesia** resmi dari Pusat Vulkanologi dan Mitigasi Bencana Geologi (PVMBG), Badan Geologi - Kementerian ESDM.\n\n"
                "Layanan utama yang dapat saya bantu meliputi:\n"
                "1. 🌋 **Status Aktivitas Gunung Api**: Pemantauan real-time status Level I (Normal) hingga Level IV (Awas) untuk 69 gunung api aktif di Indonesia beserta radius rekomendasi bahaya.\n"
                "2. 📊 **Laporan Erupsi & VAR/VONA**: Informasi riwayat letusan terbaru dan laporan evaluasi harian gunung api.\n"
                "3. 🌐 **Gempa Bumi & Tsunami**: Laporan kejadian gempa bumi penting terkini, analisis geologis, dan panduan mitigasi keselamatan.\n"
                "4. ⚠️ **Gerakan Tanah (Longsor)**: Laporan kejadian longsor dan peta zona kerentanan gerakan tanah.\n"
                "5. 📍 **Geohazard Terdekat**: Menemukan gunung api atau potensi ancaman geologi terdekat dari posisi koordinat Anda.\n"
                "6. 📚 **Edukasi & Regulasi Kebencanaan**: Penjelasan 4 tingkatan status, SOP mitigasi, dan istilah teknis vulkanologi.\n\n"
                "Silakan tanyakan informasi kebencanaan geologi yang Anda butuhkan!"
            )
            follow_ups = [
                {
                    "id": "fu_1",
                    "label": "Cek gunung api aktif",
                    "intent": "volcano_active_list",
                    "entity": None,
                    "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "query": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                },
                {
                    "id": "fu_2",
                    "label": "Laporan gempa bumi terbaru",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                    "query": "Daftar kejadian gempa bumi terkini",
                },
                {
                    "id": "fu_3",
                    "label": "Arti tingkatan status gunung api",
                    "intent": "volcano_status_level_explanation",
                    "entity": None,
                    "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                    "query": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                },
            ]
            return {
                "status": "success",
                "output": cap_text,
                "answer": cap_text,
                "api_call": None,
                "response": None,
                "references": None,
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": follow_ups[0]["action"],
                "intent": "CAPABILITY",
                "context": {
                    "intent": "CAPABILITY",
                    "entity": None,
                    "pending_action": follow_ups[0]["action"],
                    "executed_actions": executed_actions,
                },
            }

        # ===================================================================
        # STAGE 1: CURRENT QUERY INTENT CLASSIFICATION (PRIORITAS UTAMA)
        # Check current query first. Do not let previous context force intent/tool.
        # ===================================================================

        # 1.A. CONCEPTUAL STATUS LEVEL EXPLANATION (Strictly KB / RAG)
        # e.g.: "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
        #       "Apa arti Level II?", "Apa maksud Level 3 (Siaga)?", "Jelaskan status waspada"
        is_level_explanation = bool(
            re.search(r"\b(arti|maksud|makna|definisi|pengertian|penjelasan|jelaskan|terangkan|apa\s+itu|apa\s+yang\s+dimaksud)\b.*?\b(tingkat(?:an)?|status|level|skala|kategori)\b", text_lower)
            or re.search(r"\b(arti|maksud|makna|definisi|pengertian|penjelasan|jelaskan|apa\s+itu)\b.*?\b(level\s+(?:i{1,3}|iv|1|2|3|4)|normal|waspada|siaga|awas)\b", text_lower)
            or re.search(r"\b(apa\s+arti\s+level|apa\s+maksud\s+level|apa\s+itu\s+level|apa\s+arti\s+status|apa\s+maksud\s+status)\b", text_lower)
            or re.search(r"\b(beda|perbedaan)\b.*?\b(waspada|siaga|awas|normal)\b", text_lower)
            or re.search(r"\btingkat(?:an)?\s+status\s+gunung(?:\s+api)?\b", text_lower)
            or re.search(r"\b(arti|makna|maksud)\s+tingkat\b", text_lower)
        )

        if is_level_explanation:
            logger.info("[ROUTER] Intent: KNOWLEDGE_BASE (Status level explanation - strictly KB/RAG, NO status API call)")
            kb_res = KnowledgeBaseTool.execute(user_input)
            ai_output = AnswerGenerator.generate(
                user_input=user_input,
                tool_output=kb_res["output"],
                tool_name="KNOWLEDGE_BASE",
                history=history,
                entity=None,
                lang=lang,
            )
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="KNOWLEDGE_BASE",
                current_entity=None,
                assistant_answer=ai_output,
                tool_results=None,
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            return {
                "status": "success",
                "output": ai_output,
                "answer": ai_output,
                "api_call": resolve_api_url("/api/v2/gunung-api/tingkat-aktivitas"),
                "response": None,
                "references": [],
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": pending_action,
                "intent": "KNOWLEDGE_BASE",
                "context": {
                    "intent": "KNOWLEDGE_BASE",
                    "entity": None,
                    "pending_action": pending_action,
                    "executed_actions": executed_actions,
                },
            }

        # 1.B. GENERAL CONCEPTUAL & GEOLOGICAL KNOWLEDGE BASE
        # e.g.: "Apa itu magma?", "Apa itu VONA?", "Bagaimana cara kerja seismometer?", "Mengapa gunung meletus?",
        #       "Bagaimana panduan mitigasi bencana erupsi gunung api?"
        is_general_concept = bool(
            re.search(r"\b(apa\s+itu|apa\s+definisi|apa\s+pengertian|apa\s+fungsi|bagaimana\s+cara\s+kerja|mengapa|kenapa)\b.*?\b(magma|lahar|lava|vona|seismometer|seismograf|kawah|kaldera|tektonik|vulkanik|pvmbg|badan\s+geologi)\b", text_lower)
            or re.search(r"\b(prosedur|sop|aturan|kebijakan|panduan|langkah|tata\s+cara|cara)\b.*?\b(evakuasi|mitigasi|tanggap\s+darurat|penanggulangan|keselamatan)\b", text_lower)
            or re.search(r"\b(mitigasi|panduan|keselamatan|antisipasi)\b.*?\b(erupsi|letusan|gunung\s+api|vulkanik)\b", text_lower)
        ) and not _detect_volcano_name(user_input, volcano_resp)

        if is_general_concept:
            logger.info("[ROUTER] Intent: KNOWLEDGE_BASE (General concept/SOP - strictly KB)")
            kb_res = KnowledgeBaseTool.execute(user_input)
            ai_output = AnswerGenerator.generate(
                user_input=user_input,
                tool_output=kb_res["output"],
                tool_name="KNOWLEDGE_BASE",
                history=history,
                entity=None,
                lang=lang,
            )
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="KNOWLEDGE_BASE",
                current_entity=None,
                assistant_answer=ai_output,
                tool_results=None,
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            return {
                "status": "success",
                "output": ai_output,
                "answer": ai_output,
                "api_call": resolve_api_url("/api/v2/gunung-api"),
                "response": None,
                "references": [],
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": pending_action,
                "intent": "KNOWLEDGE_BASE",
                "context": {
                    "intent": "KNOWLEDGE_BASE",
                    "entity": None,
                    "pending_action": pending_action,
                    "executed_actions": executed_actions,
                },
            }

        # 1.C. EARTHQUAKE & TSUNAMI QUERIES
        is_quake = bool(re.search(r"\b(gempa|gempabumi|tsunami|seismik)\b", text_lower))
        if is_quake:
            is_mitigation = bool(
                re.search(r"\b(mitigasi|panduan|keselamatan|langkah|antisipasi|tindakan|apa yang harus dilakukan)\b", text_lower)
            )
            intent_val = "EARTHQUAKE_MITIGATION" if is_mitigation else "EARTHQUAKE"
            if is_mitigation:
                logger.info("[ROUTER] Intent: EARTHQUAKE_MITIGATION")
                result = EarthquakeMitigationTool.execute()
                ai_text = AnswerGenerator.generate(
                    user_input=user_input,
                    tool_output=result["output"],
                    tool_name="EARTHQUAKE_MITIGATION",
                    history=history,
                    entity=None,
                    lang=lang,
                )
            else:
                logger.info("[ROUTER] Intent: EARTHQUAKE")
                result = EarthquakeTool.execute(user_input, geo_location)
                ai_text = AnswerGenerator.generate(
                    user_input=user_input,
                    tool_output=result["output"],
                    tool_name="EARTHQUAKE",
                    history=history,
                    entity=None,
                    lang=lang,
                )

            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent=intent_val,
                current_entity=None,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = None
            result["pending_action"] = pending_action
            result["intent"] = intent_val
            result["context"] = {
                "intent": intent_val,
                "entity": None,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        # 1.D. GROUND MOVEMENT / LANDSLIDE QUERIES
        is_ground_movement = bool(
            re.search(r"\b(gerak(?:an)?\s*tanah|tanah\s*longsor|longsor|amblas(?:an)?|galodo|landslide|sigertan)\b", text_lower)
        )
        if is_ground_movement:
            is_mitigation = bool(
                re.search(r"\b(mitigasi|panduan|keselamatan|langkah|antisipasi|tindakan|pencegahan|cara\s+mencegah|apa\s+yang\s+harus\s+dilakukan|edukasi|ciri|tanda|gejala|faktor|penyebab)\b", text_lower)
            )
            intent_val = "GROUND_MOVEMENT_MITIGATION" if is_mitigation else "GROUND_MOVEMENT"
            if is_mitigation:
                logger.info("[ROUTER] Intent: GROUND_MOVEMENT_MITIGATION")
                result = GroundMovementMitigationTool.execute()
                ai_text = AnswerGenerator.generate(
                    user_input=user_input,
                    tool_output=result["output"],
                    tool_name="GROUND_MOVEMENT_MITIGATION",
                    history=history,
                    entity=None,
                    lang=lang,
                )
            else:
                logger.info("[ROUTER] Intent: GROUND_MOVEMENT")
                result = GroundMovementTool.execute(user_input)
                ai_text = AnswerGenerator.generate(
                    user_input=user_input,
                    tool_output=result["output"],
                    tool_name="GROUND_MOVEMENT",
                    history=history,
                    entity=None,
                    lang=lang,
                )

            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent=intent_val,
                current_entity=None,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = None
            result["pending_action"] = pending_action
            result["intent"] = intent_val
            result["context"] = {
                "intent": intent_val,
                "entity": None,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        # 1.E. LOCATION & PERSONAL SAFETY QUERIES
        loc_mode = detect_location_question(user_input, lang)
        if loc_mode:
            logger.info(f"[ROUTER] Intent: LOCATION_SAFETY (mode: {loc_mode})")
            result = LocationTool.execute(
                user_input=user_input,
                geo_location=geo_location,
                location_name=location_name,
                location_accuracy=location_accuracy,
                history=history,
                lang=lang,
            )
            ai_text = result["output"]
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="LOCATION_SAFETY",
                current_entity=None,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = None
            result["pending_action"] = pending_action
            result["context"] = {
                "intent": "LOCATION_SAFETY",
                "entity": None,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        # 1.F. VOLCANO ENTITY DETECTION & UNRECOGNIZED MOUNTAIN HANDLING
        explicit_volcano = _detect_volcano_name(user_input, volcano_resp) if volcano_resp else None

        has_volcano_term = bool(re.search(r"\bgunung(?:\s+api|\s+berapi)?\b", text_lower))
        has_aggregate_term = bool(
            re.search(r"\b(seluruh|semua|daftar|daftarkan|list|tampilkan|tampilkanlah|sebutkan|sebutkanlah|apa\s+saja|mana\s+saja|ada\s+berapa|banyaknya|katalog|rangkuman)\b", text_lower)
            or re.search(r"\b(aktif|berapi|keaktifan|elevasi|waspada|siaga|awas|normal)\b", text_lower)
        )
        has_indonesia_context = bool(re.search(r"\b(di\s+indonesia|indonesia|nusantara|nasional)\b", text_lower))

        is_explicit_aggregate = bool(
            (has_volcano_term and (
                re.search(r"\b(seluruh|semua|daftar|daftarkan|list|tampilkan|tampilkanlah|sebutkan|sebutkanlah|apa\s+saja|mana\s+saja)\b", text_lower)
                or (has_indonesia_context and not explicit_volcano)
            ))
            or bool(re.search(r"\b(?:gunung|gunungapi|gunung\s+api)\s+(?:yang\s+)?(?:berstatus\s+|status\s+|level\s+)?(waspada|siaga|awas|normal|aktif)\b", text_lower))
            or bool(re.search(r"\b(?:daftar|daftarkan|list|tampilkan|tampilkanlah|sebutkan|sebutkanlah)\s+(?:gunung|gunung\s+api)\s+(?:berstatus\s+)?(waspada|siaga|awas|normal|aktif)\b", text_lower))
            or bool(re.search(r"\b(?:berstatus|status|level)\s+(waspada|siaga|awas|normal)\b", text_lower))
        )

        GENERIC_VOLCANO_WORDS = {
            "api", "berapi", "gunungapi", "aktif", "keaktifan", "seluruh", "semua", "daftar",
            "daftarkan", "list", "katalog", "rangkuman", "indonesia", "terdekat", "apa", "saja", "mana",
            "yang", "tertinggi", "terbesar", "nusantara", "tersebut", "ini", "itu", "nasional",
            "wilayah", "daerah", "provinsi", "bencana", "di", "ke", "dari", "pada", "dalam",
            "untuk", "dengan", "dan", "atau", "ada", "berstatus", "status", "level", "tingkat",
            "waspada", "siaga", "awas", "normal", "tampilkan", "tampilkanlah", "sebutkan", "sebutkanlah"
        }
        named_mount_match = re.search(r"\b(?:gunung|gn|g)\.?\s+([a-zA-Z\s\-]+)", text_lower)
        tokens_after_gunung = []
        if named_mount_match and not is_explicit_aggregate:
            tokens_after_gunung = [
                w for w in re.findall(r"\b[a-z]+\b", named_mount_match.group(1))
                if w not in GENERIC_VOLCANO_WORDS and w not in STOPWORDS
            ]

        # If user explicitly searched for a named mountain, but it's not found in the 69 active volcanoes of PVMBG:
        if not is_explicit_aggregate and not explicit_volcano and tokens_after_gunung:
            cand_search = " ".join(tokens_after_gunung)
            # Find closest fuzzy candidate in PVMBG catalog
            best_cand_name = None
            best_cand_code = None
            best_cand_score = 0
            if volcano_resp:
                for v in volcano_resp:
                    v_name = (v.get("ga_nama_gapi") or "").lower()
                    clean_v = re.sub(r"\b(gunung|gn|g)\.?\b", "", v_name).strip()
                    score = fuzz.ratio(cand_search, clean_v)
                    for part in clean_v.split():
                        part_score = fuzz.ratio(cand_search, part)
                        if part_score > score:
                            score = part_score
                    if score > best_cand_score:
                        best_cand_score = score
                        best_cand_name = v.get("ga_nama_gapi")
                        best_cand_code = v.get("ga_code")

            if best_cand_score >= 60 and best_cand_name:
                unrec_text = (
                    f"Gunung **{cand_search.title()}** tidak ditemukan dalam database pemantauan resmi PVMBG - Badan Geologi.\n\n"
                    f"🤔 Apakah yang Anda maksud adalah **Gunung {best_cand_name}**?\n\n"
                    "Saat ini PVMBG memantau 69 gunung api aktif di Indonesia. Anda dapat mengecek status gunung yang disarankan di bawah ini."
                )
                suggested_followups = [
                    f"Bagaimana status Gunung {best_cand_name}?",
                    "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "Daftar kejadian gempa bumi terkini"
                ]
            else:
                unrec_text = (
                    f"Gunung **{cand_search.title()}** tidak ditemukan dalam daftar 69 gunung api aktif yang dipantau resmi oleh PVMBG - Badan Geologi di Indonesia.\n\n"
                    "Sistem MAGMA AI khusus melayani pemantauan aktivitas gunung api di wilayah Republik Indonesia (seperti Gunung Gede, Merapi, Semeru, Sinabung, Anak Krakatau, dll).\n\n"
                    "Silakan periksa kembali ejaan nama gunung, atau pilih informasi di bawah ini:"
                )
                suggested_followups = [
                    "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "Bagaimana status Gunung Gede?",
                    "Bagaimana status Gunung Merapi?"
                ]

            follow_ups = [
                {
                    "id": f"fu_{i+1}",
                    "label": act[:50],
                    "intent": "volcano_status" if "Gunung" in act else "volcano_active_list",
                    "entity": best_cand_name if ("Gunung" in act and best_cand_name) else None,
                    "action": act,
                    "query": act,
                }
                for i, act in enumerate(suggested_followups)
            ]
            return {
                "status": "success",
                "output": unrec_text,
                "answer": unrec_text,
                "api_call": None,
                "response": None,
                "references": None,
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": follow_ups[0]["action"],
                "intent": "VOLCANO_NOT_FOUND",
                "context": {
                    "intent": "VOLCANO_NOT_FOUND",
                    "entity": None,
                    "pending_action": follow_ups[0]["action"],
                    "executed_actions": executed_actions,
                },
            }

        # 1.G. AGGREGATE VOLCANO LIST & CATALOG QUERIES (MAGMA API)
        # e.g.: "Tampilkan seluruh gunung api di indonesia", "Daftar gunung api",
        #       "Gunung apa saja yang aktif?", "Sebutkan semua gunung di indonesia"
        has_volcano_term = bool(re.search(r"\bgunung(?:\s+api|\s+berapi)?\b", text_lower))
        has_aggregate_term = bool(
            re.search(r"\b(seluruh|semua|daftar|list|tampilkan|sebutkan|apa\s+saja|mana\s+saja|ada\s+berapa|banyaknya|katalog|rangkuman)\b", text_lower)
            or re.search(r"\b(aktif|berapi|keaktifan|elevasi|waspada|siaga|awas)\b", text_lower)
        )
        has_indonesia_context = bool(re.search(r"\b(di\s+indonesia|indonesia|nusantara|nasional)\b", text_lower))

        is_explicit_single_volcano = bool(
            explicit_volcano
            and not re.search(r"\b(seluruh|semua|daftar|list|apa\s+saja|mana\s+saja)\b", text_lower)
        )

        is_aggregate_volcano_query = (
            is_explicit_aggregate
            or (has_volcano_term and (has_aggregate_term or has_indonesia_context))
            or check_if_mount_level(user_input)
            or bool(re.search(r"^\s*(daftar\s+|daftarkan\s+|tampilkan\s+|sebutkan\s+)?gunung(\s+api)?(\s+aktif)?\s*$", text_lower))
            or bool(re.search(r"\bgunung(\s+api)?\s+aktif\b", text_lower))
        ) and not is_explicit_single_volcano and not tokens_after_gunung

        if is_aggregate_volcano_query:
            logger.info("[ROUTER] Intent: VOLCANO_ACTIVE_LIST")
            result = VolcanoActiveListTool.execute(user_input)
            ai_text = result["output"]
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="VOLCANO_ACTIVE_LIST",
                current_entity=None,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = None
            result["pending_action"] = pending_action
            result["context"] = {
                "intent": "VOLCANO_ACTIVE_LIST",
                "entity": None,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        # ===================================================================
        # STAGE 2: VOLCANO ENTITY RESOLUTION (EXPLICIT vs ANAPHORA/CONTINUITY)
        # ===================================================================
        detected_codes = _detect_volcano_name(user_input, volcano_resp) if volcano_resp else None
        if not detected_codes:
            single_code = detect_volcano_name(user_input)
            detected_codes = [single_code] if single_code else None

        volcano_code = detected_codes[0] if detected_codes else None
        volcano_name = None
        if volcano_code and volcano_resp:
            matched_v = next((v for v in volcano_resp if (v.get("ga_code") or "").upper() == volcano_code.upper()), None)
            if matched_v:
                volcano_name = matched_v.get("ga_nama_gapi")
            else:
                volcano_code = None
        else:
            volcano_code = None

        # Entity Continuity & Anaphora Resolution:
        # Only inherit entity if query is anaphoric/demonstrative or short follow-up!
        if not volcano_code and history:
            is_anaphoric_followup = bool(
                re.search(r"\b(gunung\s+(?:tersebut|itu|ini))\b", text_lower)
                or re.search(r"\b(rekomendasi(?:nya)?|kondisi(?:nya)?|status(?:nya)?|kegempaan(?:nya)?|kabar(?:nya)?|erupsi(?:nya)?|letusan(?:nya)?|seismisitas(?:nya)?)\b", text_lower)
                or re.search(r"\b(bagaimana\s+rekomendasi|bagaimana\s+kondisi|bagaimana\s+status|bagaimana\s+kabarnya|bagaimana\s+kegempaannya)\b", text_lower)
                or re.search(r"\b(kapan\s+terakhir(?:nya)?|kapan\s+meletus|yang\s+terakhir)\b", text_lower)
                or re.search(r"\b(berapa\s+radius|berapa\s+jarak\s+aman|radius\s+aman(?:nya)?)\b", text_lower)
            )
            if is_anaphoric_followup:
                hist_code, hist_name = extract_active_entity_from_history(history, volcano_resp)
                if hist_code:
                    volcano_code = hist_code
                    volcano_name = hist_name
                    logger.info(f"[ROUTER] Inherited active entity from history via anaphora: {volcano_name} ({volcano_code})")

        # ===================================================================
        # STAGE 3: VOLCANO TOOL EXECUTION
        # ===================================================================
        is_asking_eruption = bool(
            re.search(r"\b(erupsi|letusan|meletus|erupt|letus)\b", text_lower)
            or (volcano_code and re.search(r"\b(kapan|kapanpun|terakhir|yang\s+terakhir)\b", text_lower))
        )
        if is_asking_eruption:
            logger.info(f"[ROUTER] Intent: VOLCANO_ERUPTION (code: {volcano_code}, name: {volcano_name})")
            result = VolcanoEruptionTool.execute(
                volcano_code=volcano_code,
                volcano_name=volcano_name,
                user_input=user_input,
                volcano_resp=volcano_resp,
                lang=lang,
            )
            ai_text = AnswerGenerator.generate(
                user_input=user_input,
                tool_output=result["output"],
                tool_name="VOLCANO_ERUPTION",
                history=history,
                entity=volcano_name,
                lang=lang,
            )
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="VOLCANO_ERUPTION",
                current_entity=volcano_name,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = volcano_name
            result["pending_action"] = pending_action
            result["context"] = {
                "intent": "VOLCANO_ERUPTION",
                "entity": volcano_name,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        clean_mitigation_text = re.sub(r"pusat vulkanologi dan mitigasi bencana geologi", "", text_lower)
        clean_mitigation_text = re.sub(r"\bpvmbg\b", "", clean_mitigation_text)
        is_asking_procedure_or_mitigation = bool(
            re.search(r"\b(prosedur|sop|panduan|mitigasi|evakuasi|aturan|kebijakan|penanganan|cara kerja)\b", clean_mitigation_text)
        )
        if is_asking_procedure_or_mitigation and volcano_code:
            logger.info(f"[ROUTER] Multi-Tool: VOLCANO_STATUS + KNOWLEDGE_BASE for {volcano_name}")
            v_res = VolcanoStatusTool.execute(volcano_code, volcano_resp, user_input, lang)
            kb_res = KnowledgeBaseTool.execute(f"mitigasi erupsi gunung api {volcano_name}")
            combined_data = f"DATA STATUS REALTIME DARI SISTEM PVMBG:\n{v_res['output']}\n\nDATA PANDUAN / DOKUMEN RESMI MITIGASI:\n{kb_res['output']}"
            ai_output = AnswerGenerator.generate(
                user_input=user_input,
                tool_output=combined_data,
                tool_name="VOLCANO_STATUS_AND_KNOWLEDGE_BASE",
                history=history,
                entity=volcano_name,
                lang=lang,
            )
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="VOLCANO_STATUS_AND_KNOWLEDGE_BASE",
                current_entity=volcano_name,
                assistant_answer=ai_output,
                tool_results={"volcano": v_res.get("response")},
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            return {
                "status": "success",
                "output": ai_output,
                "answer": ai_output,
                "api_call": v_res.get("api_call"),
                "response": v_res.get("response"),
                "references": [],
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": volcano_name,
                "pending_action": pending_action,
                "intent": "VOLCANO_STATUS_AND_KNOWLEDGE_BASE",
                "context": {
                    "intent": "VOLCANO_STATUS_AND_KNOWLEDGE_BASE",
                    "entity": volcano_name,
                    "pending_action": pending_action,
                    "executed_actions": executed_actions,
                },
            }

        # Specific Volcano Status & Recommendation Queries
        is_asking_status = bool(
            re.search(r"\b(status|level|tingkat|rekomendasi|kondisi|kabar|info|kegempaan|seismik)\b", text_lower)
            or (volcano_code is not None)
        )
        if is_asking_status and volcano_code:
            logger.info(f"[ROUTER] Intent: VOLCANO_STATUS (code: {volcano_code}, entity: {volcano_name})")
            result = VolcanoStatusTool.execute(
                volcano_code=volcano_code,
                volcano_resp=volcano_resp,
                user_input=user_input,
                lang=lang,
            )
            ai_text = result["output"]
            if tokens_after_gunung and volcano_name:
                q_token = " ".join(tokens_after_gunung).lower()
                if q_token != volcano_name.lower() and not ai_text.startswith("*("):
                    ai_text = f"*(Menampilkan status aktivitas **Gunung {volcano_name}** berdasarkan pencarian Anda)*\n\n{ai_text}"

            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="VOLCANO_STATUS",
                current_entity=volcano_name,
                assistant_answer=ai_text,
                tool_results=result.get("response"),
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            result["output"] = ai_text
            result["answer"] = ai_text
            result["follow_ups"] = follow_ups
            result["suggested_follow_ups"] = [it["action"] for it in follow_ups]
            result["entity"] = volcano_name
            result["pending_action"] = pending_action
            result["context"] = {
                "intent": "VOLCANO_STATUS",
                "entity": volcano_name,
                "pending_action": pending_action,
                "executed_actions": executed_actions,
            }
            return result

        # Fallback: Check if query is OUT_OF_SCOPE or Knowledge Base
        GEOLOGICAL_TERMS = {
            "gunung", "gempa", "tsunami", "longsor", "tanah", "vulkanik", "seismik",
            "magma", "lahar", "lava", "kawah", "kaldera", "erupsi", "letusan", "geologi",
            "pvmbg", "esdm", "mitigasi", "bencana", "status", "level", "waspada", "siaga",
            "awas", "normal", "aman", "pendakian", "vona", "var", "amblasan", "lindu",
            "retakan", "koordinat", "lokasi", "bahaya", "radius", "jarak", "evakuasi",
            "sesar", "patahan", "tremor", "tektonik", "kegempaan", "batu", "abu"
        }
        query_words = set(re.findall(r"\b[a-z]+\b", text_lower))
        has_geological_topic = bool(query_words & GEOLOGICAL_TERMS)
        is_confirmation = clean_q in {"ya", "iya", "yaa", "boleh", "ok", "oke", "lanjut", "tidak", "gak", "nggak"}
        has_official_kb = any(doc["matches"](user_input) for doc in OFFICIAL_PVMBG_KNOWLEDGE_DOCS)

        # Fast-path: If query has no geological keywords and no official KB match, handle immediately as OUT_OF_SCOPE
        if not has_geological_topic and not is_confirmation and not has_official_kb:
            logger.info("[ROUTER] Intent: OUT_OF_SCOPE (Non-geological query)")
            out_of_scope_text = (
                "Pertanyaan Anda berada di luar ruang lingkup pemantauan kebencanaan geologi.\n\n"
                "Sebagai **Asisten AI MAGMA Indonesia** (Pusat Vulkanologi dan Mitigasi Bencana Geologi / PVMBG - Badan Geologi, Kementerian ESDM), layanan resmi saya berfokus pada:\n"
                "1. 🌋 **Status Aktivitas Gunung Api**: Pemantauan 69 gunung api aktif di Indonesia dan rekomendasi keselamatan.\n"
                "2. 🌐 **Laporan Gempa Bumi & Tsunami**: Laporan kejadian terkini serta analisis geologis.\n"
                "3. ⚠️ **Gerakan Tanah (Longsor)**: Laporan kejadian dan peta zona potensi bahaya.\n"
                "4. 📍 **Pengecekan Ancaman Geologi Terdekat**: Berdasarkan posisi koordinat Anda.\n"
                "5. 📋 **Panduan Mitigasi & Keselamatan**: Prosedur darurat menghadapi bencana geologi.\n\n"
                "Apakah ada informasi terkait kebencanaan geologi yang ingin Anda ketahui?"
            )
            follow_ups = [
                {
                    "id": "fu_1",
                    "label": "Cek status gunung api aktif",
                    "intent": "volcano_active_list",
                    "entity": None,
                    "action": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                    "query": "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
                },
                {
                    "id": "fu_2",
                    "label": "Laporan gempa bumi terbaru",
                    "intent": "earthquake_list",
                    "entity": None,
                    "action": "Daftar kejadian gempa bumi terkini",
                    "query": "Daftar kejadian gempa bumi terkini",
                },
                {
                    "id": "fu_3",
                    "label": "Penjelasan tingkatan status gunung api",
                    "intent": "volcano_status_level_explanation",
                    "entity": None,
                    "action": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                    "query": "Jelaskan arti tingkatan status gunung api dari normal hingga awas",
                },
            ]
            return {
                "status": "success",
                "output": out_of_scope_text,
                "answer": out_of_scope_text,
                "api_call": None,
                "response": None,
                "references": None,
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": follow_ups[0]["action"],
                "intent": "OUT_OF_SCOPE",
                "context": {
                    "intent": "OUT_OF_SCOPE",
                    "entity": None,
                    "pending_action": follow_ups[0]["action"],
                    "executed_actions": executed_actions,
                },
            }

        # Fallback to Knowledge Base for geological queries
        kb_res = KnowledgeBaseTool.execute(user_input)
        if kb_res.get("status") == "success":
            ai_output = AnswerGenerator.generate(
                user_input=user_input,
                tool_output=kb_res["output"],
                tool_name="KNOWLEDGE_BASE",
                history=history,
                entity=None,
                lang=lang,
            )
            follow_ups = FollowUpGenerator.generate(
                conversation_history=history,
                current_query=user_input,
                current_intent="KNOWLEDGE_BASE",
                current_entity=None,
                assistant_answer=ai_output,
                tool_results=None,
                available_tools=AVAILABLE_TOOLS_SPEC,
                executed_actions=executed_actions,
                lang=lang,
            )
            pending_action = follow_ups[0]["action"] if follow_ups else None
            return {
                "status": "success",
                "output": ai_output,
                "answer": ai_output,
                "api_call": resolve_api_url("/api/v2/gunung-api"),
                "response": None,
                "references": [],
                "follow_ups": follow_ups,
                "suggested_follow_ups": [it["action"] for it in follow_ups],
                "entity": None,
                "pending_action": pending_action,
                "intent": "KNOWLEDGE_BASE",
                "context": {
                    "intent": "KNOWLEDGE_BASE",
                    "entity": None,
                    "pending_action": pending_action,
                    "executed_actions": executed_actions,
                },
            }

        return None

