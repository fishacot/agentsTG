"""Validate .cursor rules, commands, and optional skills (stdlib only)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CURSOR = _ROOT / ".cursor"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
_SKILL_TITLE_RE = re.compile(r"^#\s+\S", re.MULTILINE)
_SKILL_WHEN_RE = re.compile(
    r"(?im)^#{1,3}\s+(when to use|когда использовать)\b"
)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def _validate_mdc(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    if not fm:
        errors.append(f"{path}: missing YAML frontmatter (--- ... ---)")
        return
    if not fm.get("description"):
        errors.append(f"{path}: frontmatter missing 'description'")
    if "alwaysApply" not in fm and "globs" not in fm:
        errors.append(
            f"{path}: frontmatter needs 'alwaysApply' or 'globs'"
        )


def _validate_command(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{path}: command file missing")
        return
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        errors.append(f"{path}: command file is empty")


def _validate_skill(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not _SKILL_TITLE_RE.search(text):
        errors.append(f"{path}: missing title (# heading)")
    if not _SKILL_WHEN_RE.search(text):
        errors.append(
            f"{path}: missing 'When to use' / 'Когда использовать' section"
        )


def main() -> int:
    errors: list[str] = []

    rules_dir = _CURSOR / "rules"
    if rules_dir.is_dir():
        mdc_files = sorted(rules_dir.glob("*.mdc"))
        if not mdc_files:
            errors.append(f"{rules_dir}: no *.mdc files found")
        for path in mdc_files:
            _validate_mdc(path, errors)
    else:
        errors.append(f"{rules_dir}: directory missing")

    commands_dir = _CURSOR / "commands"
    if commands_dir.is_dir():
        cmd_files = sorted(commands_dir.glob("*.md"))
        if not cmd_files:
            errors.append(f"{commands_dir}: no *.md command files found")
        for path in cmd_files:
            _validate_command(path, errors)
    else:
        errors.append(f"{commands_dir}: directory missing")

    skills_root = _CURSOR / "skills"
    if skills_root.is_dir():
        for skill in sorted(skills_root.glob("**/SKILL.md")):
            _validate_skill(skill, errors)

    if errors:
        print("validate_cursor_artifacts: FAILED", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("validate_cursor_artifacts: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
