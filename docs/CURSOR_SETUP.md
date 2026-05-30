# Настройка Cursor с CursoRules

## 1. Скопировать правила

Из корня **вашего проекта** (не из папки CursoRules как отдельного workspace):

```powershell
Copy-Item -Recurse -Force CursoRules\.cursor .cursor
```

## 2. Файлы в проекте

| Файл в корне проекта | Источник |
|----------------------|----------|
| `docs/implementation-notes.md` | `CursoRules/docs/implementation-notes.TEMPLATE.md` |
| `docs/PROJECT_VERIFICATION.md` | `CursoRules/docs/VERIFICATION_TEMPLATE.md` |
| `docs/TASK_TEMPLATE.md` | опционально, копия из CursoRules |

## 3. Custom Commands

Cursor → Settings → Commands → импорт из `.cursor/commands/`:

- agent-preflight
- agent-postflight
- agent-verify (настройте под свои команды в PROJECT_VERIFICATION)
- agent-task-intake
- agent-confirm-acceptance
- **agent-implementation-notes**

## 4. User Rules (глобально, опционально)

В Cursor Settings → Rules можно добавить одну строку:

> При реализации SPEC веди docs/implementation-notes.md (см. implementation-notes.mdc в проекте).

## 5. CursoRules не трогать при обычной разработке

Меняйте `CursoRules/` только когда улучшаете **сам пакет правил**, а не код приложения.

## 6. Расширения IDE

Файлы: **`.vscode/extensions.json`**, **`.vscode/settings.json`**.

Установка всех рекомендованных (предпочтительно через UI):

1. **Cursor → Extensions** (Ctrl+Shift+X) → баннер **«Install Recommended Extensions»** (появится при открытии проекта).
2. Или CLI (если marketplace отвечает):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-cursor-extensions.ps1
```

Если `cursor --install-extension` зависает или `ETIMEDOUT` — установите вручную из Extensions по ID из `.vscode/extensions.json`.

Ключевые: Python, Pylance, Ruff, markdownlint, TOML, YAML, GitLens, Docker, Error Lens, Remote SSH.

## 7. Hooks (Cursor Team Kit pattern)

- **`.cursor/hooks.json`** — ruff после правок `.py`, guard destructive shell, verify на stop.
- Settings → **Hooks** — проверить что hooks активны; после правок `hooks.json` — Reload Window.

## 8. Cursor Team Kit (плагин)

Установлен глобально (`/add-plugin cursor-team-kit`). Для agentsTG см. правило **`.cursor/rules/team-kit-workflow.mdc`**.

Полезные skills: `verify-this`, `fix-ci`, `review-and-ship`, `deslop`. Subagents: `ci-watcher`, `thermo-nuclear-code-quality-review`.

## 9. Markdown verify (docs)

```powershell
npm install
npm run verify
```
