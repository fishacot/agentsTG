"""HTTP API token gate — fail closed without token unless DEBUG."""

from src.agents_tg.services.health_server import _check_api_token


def test_api_token_required_when_not_debug(monkeypatch):
    monkeypatch.setenv("AGENT_RUN_API_TOKEN", "")
    monkeypatch.setenv("DEBUG", "false")
    assert _check_api_token("") is False


def test_api_token_bypass_only_in_debug(monkeypatch):
    monkeypatch.setenv("AGENT_RUN_API_TOKEN", "")
    monkeypatch.setenv("DEBUG", "true")
    assert _check_api_token("") is True


def test_api_token_bearer_match(monkeypatch):
    monkeypatch.setenv("AGENT_RUN_API_TOKEN", "secret")
    monkeypatch.setenv("DEBUG", "false")
    headers = "Authorization: Bearer secret\r\n"
    assert _check_api_token(headers) is True
    assert _check_api_token("Authorization: Bearer wrong\r\n") is False
