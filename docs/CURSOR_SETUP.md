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
