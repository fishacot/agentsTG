"""Confirmation UI parsing for Telegram inline delivery."""

from __future__ import annotations

import json

from src.agents_tg.services.confirmation_delivery import (
    ConfirmationUI,
    parse_confirmation_from_tool_output,
)


def test_parse_confirmation_ok() -> None:
    payload = {
        "ok": False,
        "needs_confirmation": True,
        "hint": "Подтвердите завершение проекта",
        "inline_keyboard": {
            "inline_keyboard": [[{"text": "OK", "callback_data": "confirm:abc"}]]
        },
    }
    ui = parse_confirmation_from_tool_output(json.dumps(payload))
    assert isinstance(ui, ConfirmationUI)
    assert ui.text == "Подтвердите завершение проекта"
    assert ui.reply_markup["inline_keyboard"][0][0]["callback_data"] == "confirm:abc"


def test_parse_confirmation_missing_markup() -> None:
    payload = {"needs_confirmation": True, "hint": "x"}
    assert parse_confirmation_from_tool_output(json.dumps(payload)) is None


def test_parse_confirmation_not_json() -> None:
    assert parse_confirmation_from_tool_output("not json") is None
