# Правила Cursor (CursoRules)

Полный контракт: **`../AGENTS.md`**. Установка: **`../docs/CURSOR_SETUP.md`**.

## Rules

| Файл | alwaysApply | Назначение |
|------|-------------|------------|
| `agent-workflow-core.mdc` | да | План → diff → verify → журнал |
| `implementation-notes.mdc` | да | `docs/implementation-notes.md` в workspace (Thariq) |
| `task-closure-protocol.mdc` | да | Приёмка, 3 цикла verify |
| `security-trust.mdc` | да | Секреты |
| `markdown-prompts.mdc` | `**/*.md` | Markdown |
| `cursor-mdc-authoring.mdc` | `.mdc` | Оформление правил |
| `package-json-ci.mdc` | package.json | CI npm (если есть) |
| `github-actions.mdc` | workflows | GitHub Actions |
| `dependabot-config.mdc` | dependabot | Dependabot |
| `team-kit-workflow.mdc` | да | Cursor Team Kit → Python workflow |

## Hooks

| Файл | Событие | Назначение |
|------|---------|------------|
| `hooks/ruff_after_py_edit.py` | afterFileEdit | Быстрый ruff check после правок `.py` |
| `hooks/guard_destructive_shell.py` | beforeShellExecution | Подтверждение force-push / rm -rf |
| `hooks/stop_verify_reminder.py` | *(отключён)* | ~~stop~~ — напоминание pytest + notes; убран из `hooks.json` по запросу |

Конфиг: **`hooks.json`**. После правок перезагрузите окно Cursor (Hooks tab).

## IDE (`.vscode/`)

Рекомендуемые расширения — **`../.vscode/extensions.json`**. Установка:

```powershell
# Предпочтительно: Extensions → «Install Recommended Extensions»
powershell -ExecutionPolicy Bypass -File scripts/install-cursor-extensions.ps1
```

preflight · plan-deep · verify · postflight · task-intake · confirm-acceptance · **implementation-notes**

## Активация

Скопируй эту папку `.cursor` в **корень вашего проекта**. CursoRules при этом может оставаться подпапкой.
