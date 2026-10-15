"""Regression tests for WhatsApp reply format versus incoming audio format."""

import asyncio
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks

from models.whatsapp_auth_session import WhatsAppAuthSession
from routes.v1 import whatsapp


class FakeSession:
    def __init__(self, state):
        self.state = state

    async def get(self, _model, _session_id):
        return self.state

    async def commit(self):
        pass


class WhatsAppVoiceModeTests(unittest.TestCase):
    def setUp(self):
        self.state = WhatsAppAuthSession(
            session_id="whatsapp-test-voice-mode",
            state="anonymous",
            conversation_mode="auto",
            voice_mode=True,
        )
        self.db = FakeSession(self.state)

    def send(self, user_input="", audio_base64=None):
        tasks = BackgroundTasks()
        request = whatsapp.WhatsAppAnalyzeRequest(
            session_id=self.state.session_id,
            user_input=user_input,
            audio_base64=audio_base64,
        )
        with patch.object(whatsapp, "transcribe_base64_audio", return_value="halo"):
            response = asyncio.run(
                whatsapp.analyze_whatsapp(
                    request, tasks, api_key={"token": "test"}, db=self.db
                )
            )
        return response, tasks

    def test_voice_off_keeps_incoming_voice_note_text_only(self):
        response, tasks = self.send("/voice off")
        self.assertFalse(self.state.voice_mode)
        self.assertIn("teks saja", response["output"])
        self.assertEqual(tasks.tasks, [])

        response, tasks = self.send(audio_base64="ZHVtbXk=")
        self.assertIn("Pesan Suara", response["output"])
        self.assertEqual(tasks.tasks, [])

    def test_text_command_keeps_incoming_voice_note_text_only(self):
        self.send("/text")
        self.assertFalse(self.state.voice_mode)
        _, tasks = self.send(audio_base64="ZHVtbXk=")
        self.assertEqual(tasks.tasks, [])

    def test_voice_on_sends_audio_for_incoming_voice_note(self):
        self.state.voice_mode = False
        self.send("/voice")
        self.assertTrue(self.state.voice_mode)
        _, tasks = self.send(audio_base64="ZHVtbXk=")
        self.assertEqual(len(tasks.tasks), 1)

    def test_inline_voice_command_applies_to_same_answer(self):
        self.state.voice_mode = False
        _, tasks = self.send("/voice halo")
        self.assertTrue(self.state.voice_mode)
        self.assertEqual(len(tasks.tasks), 1)


if __name__ == "__main__":
    unittest.main()
