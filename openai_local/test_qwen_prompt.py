"""Prompt-format tests; no model weights need to be loaded."""
from config import config
from models import ChatMessage
from utils import format_prompt


def test_qwen_chatml(monkeypatch):
    monkeypatch.setattr(config, "model_name", "qwen2.5-1.5b-instruct")
    messages = [
        ChatMessage(role="system", content="Use only the reference."),
        ChatMessage(role="user", content="What is his skill?"),
    ]
    assert format_prompt(messages) == (
        "<|im_start|>system\nUse only the reference.<|im_end|>\n"
        "<|im_start|>user\nWhat is his skill?<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    assert messages[0].content == "Use only the reference."


def test_qwen_followup(monkeypatch):
    monkeypatch.setattr(config, "model_name", "qwen2.5-1.5b-instruct")
    prompt = format_prompt([
        ChatMessage(role="user", content="Who is Ali?"),
        ChatMessage(role="assistant", content="Ali is a developer."),
        ChatMessage(role="user", content="His skill?"),
    ])
    assert "<|im_start|>assistant\nAli is a developer.<|im_end|>" in prompt
    assert prompt.endswith("<|im_start|>assistant\n")
