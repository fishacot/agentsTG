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

## Commands

preflight · plan-deep · verify · postflight · task-intake · confirm-acceptance · **implementation-notes**

## Активация

Скопируй эту папку `.cursor` в **корень вашего проекта**. CursoRules при этом может оставаться подпапкой.
