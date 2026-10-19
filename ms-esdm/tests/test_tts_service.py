"""Tests for text normalization before WhatsApp voice replies."""

import unittest

from services.tts_service import prepare_text_for_speech


class PrepareTextForSpeechTests(unittest.TestCase):
    def test_volcano_levels_are_spoken_as_numbers(self):
        for roman, spoken in (("I", "satu"), ("II", "dua"), ("III", "tiga"), ("IV", "empat")):
            with self.subTest(level=roman):
                result = prepare_text_for_speech(f"Status Gunung Gede: Level {roman} (Normal).")
                self.assertIn(f"Level {spoken}", result)

    def test_other_roman_numerals_are_unchanged(self):
        result = prepare_text_for_speech("Bab IV membahas Level IV (Awas).")
        self.assertIn("Bab IV", result)
        self.assertIn("Level empat", result)


if __name__ == "__main__":
    unittest.main()
