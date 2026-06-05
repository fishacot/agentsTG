---
summary: Эргономика агента — скрипты validate/docs_list/committer, skill VPS-debug
read_when: добавляете tooling для Cursor, выбираете локальный LLM, отлаживаете deploy
---

# DEV_AGENT_ERGONOMICS — agentsTG

Короткий справочник для людей и Cursor-агентов: что добавлено из идей [steipete/agent-scripts](https://github.com/steipete/agent-scripts) и как этим пользоваться. Канон процесса — [`AGENTS.md`](../AGENTS.md) / [`CursoRules/AGENTS.md`](../CursoRules/AGENTS.md).

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/validate_cursor_artifacts.py` | Проверка `.cursor/rules/*.mdc`, `commands/*.md`, опционально `skills/**/SKILL.md` |
| `scripts/docs_list.py` | Таблица/JSON по `docs/**/*.md` с frontmatter `summary`, `read_when` |
| `scripts/committer.ps1` | Безопасный commit на Windows: явные пути или `-All`, отказ при `.env` в stage |

### validate_cursor_artifacts

```powershell
python scripts/validate_cursor_artifacts.py
```

Exit 0 — OK; exit 1 — список ошибок в stderr. Запускайте после правок в `.cursor/`.

### docs_list

```powershell
python scripts/docs_list.py
python scripts/docs_list.py --json
```

Помогает агенту выбрать документ по `summary` / `read_when` без полного обхода `docs/`.

### committer.ps1

```powershell
.\scripts\committer.ps1 -Message "fix: example" src/foo.py docs/bar.md
.\scripts\committer.ps1 -Message "chore: tracked only" -All
```

Не делает `git push`. Не stage'ит `.env`. Для полного ship-пайплайна — `scripts/ship.ps1`.

## Skill: VPS debug

[`.cursor/skills/agents-tg-vps-debug/SKILL.md`](../.cursor/skills/agents-tg-vps-debug/SKILL.md) — journalctl, `_fetch_vps_logs.py`, `vps_deploy.py`, health, Elza/inbound — **без секретов**.

## Frontmatter в доках

Ключевые файлы помечены YAML в начале:

- `summary` — одна строка «о чём файл»
- `read_when` — когда агенту стоит его открыть

Скан: `python scripts/docs_list.py`.

---

## AirLLM: go/no-go для agentsTG

[AirLLM](https://github.com/lyogavin/airllm) — библиотека **послойной подгрузки** весов HuggingFace-модели с диска, чтобы уместить большие модели в ограниченную VRAM/RAM. API — **`generate()`** на HF-моделях, не OpenAI-compatible chat.

### Что у нас сейчас

| Фактор | agentsTG |
|--------|----------|
| VPS FirstByte ~91.186.221.32 | ~1 GB RAM, **CPU-only**, 7 ботов, async httpx |
| `llm_client` | OpenAI-compatible **chat completions** + **tools** (Gemini / Groq / Qwen по HTTP) |
| UX | Telegram — ответ за секунды, не минуты |
| Диск | Конвертация shard'ов AirLLM — много GB на модель |

### Почему AirLLM не подходит для prod VPS

1. **GPU / скорость** — AirLLM рассчитан на CUDA; на CPU inference крайне медленный (70B → минуты на ответ).
2. **API mismatch** — `generate()` HuggingFace, без native tool calling; переписывать orchestrator и `llm_client`.
3. **RAM / диск** — VPS ~1 GB RAM не тянет даже streaming; конвертация весов занимает десятки GB.
4. **Concurrency** — 7 ботов параллельно на одном CPU-local inference не масштабируется.
5. **Latency** — Telegram UX требует секунд, не минут.

| Verdict | **No-go для production VPS bots**; допустим только offline spike на dev-машине с GPU |

### Лучшие альтернативы (если понадобится локальный LLM)

1. **Оставить облачную цепочку** — Gemini / Groq / Qwen (текущий путь).
2. **GPU-сервер + OpenAI-прокси** — Ollama или vLLM с совместимым `/v1/chat/completions` и tool calling.
3. **llama.cpp** — только для tiny local dev / экспериментов, не для 7 prod-ботов.

**Итог:** AirLLM не интегрировать в `pyproject.toml` и `llm_client`; оценка зафиксирована здесь.

---

**См. также:** [`docs/PROJECT_VERIFICATION.md`](PROJECT_VERIFICATION.md), [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md), [`docs/implementation-notes.md`](implementation-notes.md).
