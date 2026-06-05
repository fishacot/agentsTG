"""Owner RULES.md playbook injection."""

from src.agents_tg.services.playbook import load_playbook_block, playbook_path
from src.agents_tg.services.prompts.assembler import build_system_prompt
from src.agents_tg.services.prompts.tier_rules import PromptTier


def test_playbook_path_under_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("ROOT_DIR", str(tmp_path))
    from src.agents_tg.config import settings as settings_mod

    monkeypatch.setattr(
        settings_mod,
        "get_settings",
        lambda: settings_mod.AppSettings(ROOT_DIR=tmp_path),
    )
    path = playbook_path("42")
    assert path == tmp_path / "workspace" / "users" / "42" / "RULES.md"


def test_load_playbook_block_missing_returns_empty():
    assert load_playbook_block("no-such-user-99999") == ""


def test_load_playbook_block_injects(tmp_path, monkeypatch):
    rules_dir = tmp_path / "workspace" / "users" / "7"
    rules_dir.mkdir(parents=True)
    (rules_dir / "RULES.md").write_text("Тихие часы: 22–08", encoding="utf-8")
    monkeypatch.setenv("ROOT_DIR", str(tmp_path))
    from src.agents_tg.config import settings as settings_mod

    monkeypatch.setattr(
        settings_mod,
        "get_settings",
        lambda: settings_mod.AppSettings(ROOT_DIR=tmp_path),
    )
    block = load_playbook_block("7")
    assert "playbook" in block
    assert "Тихие часы" in block


def test_assembler_includes_playbook_on_full_tier():
    prompt = build_system_prompt(
        tier=PromptTier.FULL,
        human_name="Эльза",
        designation="ассистент",
        soul="soul",
        env_block="",
        history_block="",
        memory_block="",
        playbook_block="## Правила\nБез звонков ночью",
        output_hints="",
        include_web_tools=False,
        user_id="1",
    )
    assert "Без звонков ночью" in prompt


def test_assembler_omits_playbook_on_light_tier():
    prompt = build_system_prompt(
        tier=PromptTier.LIGHT,
        human_name="Эльза",
        designation="ассистент",
        soul="soul",
        env_block="",
        history_block="",
        memory_block="",
        playbook_block="## Правила\nБез звонков",
        output_hints="",
        include_web_tools=False,
        user_id="1",
    )
    assert "Без звонков" not in prompt
