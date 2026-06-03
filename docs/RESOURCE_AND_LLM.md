# Ресурсы VPS и снижение рисков Groq

Документ для **текущего** FirstByte VPS (~1 GB RAM) и solo-владельца. Апгрейд VPS — позже; функционал должен работать и сейчас.

## Что позволяет VPS сегодня

| Ресурс | Рекомендация | Зачем |
|--------|--------------|--------|
| RAM ~1 GB | Только `agents-tg` + Python venv | Ollama / локальные LLM — **нет** |
| CPU | 7 ботов в одном процессе | Нормально для личного штаба |
| Диск | `workspace/users/{id}/` | Память **вне** Groq: NOTEBOOK, USER, MEMORY, JOURNAL |
| Neon PG | `DATABASE_URL` в `.env` | Планы, напоминания, факты — переживают рестарт |
| Upstash Redis | опционально | cooldown, dedupe, бюджет LLM |

См. [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md), [`deploy/NEON_SETUP.md`](../deploy/NEON_SETUP.md).

## Стратегия: память вне модели

Groq не «помнит» между сессиями. Вместо длинных пересказов в чате:

1. **`workspace/users/{id}/NOTEBOOK.md`** — ваш блокнот (редактируете сами или через инструмент `append_notebook`).
2. **`USER.md` / `MEMORY.md` / `memory/YYYY-MM-DD.md`** — профиль и дневник (уже есть).
3. **PG `user_facts` + `remember_about_user`** — структурированные факты.
4. **`chat_history` + `task_id`** — контекст диалога по задаче, без лишних LLM-раундов.
5. **Mem0** — только если задан `MEM0_API_KEY` (платный/облачный слой).

В промпт на FULL/STANDARD попадает **сжатый** блокнот (лимит символов), а не вся переписка.

## Риски Groq и как закрыты в коде

| Риск | Митигация |
|------|-----------|
| 429 / daily TPM | `LLM_COOLDOWN_SEC`, цепочка провайдеров, сообщение пользователю |
| Длинный план съел лимит | `MAX_PLAN_STEPS` (по умолчанию 4) |
| Много вызовов за день | `LLM_SOFT_DAILY_CALLS` — мягкий потолок на пользователя |
| Исчерпан бюджет | `GROQ_DEFER_HEAVY_ON_BUDGET` → LIGHT tier (меньше токенов) |
| Потеря контекста после 429 | Запись в NOTEBOOK через `append_notebook` / daily log |

## Рекомендуемый `.env` (VPS, Groq-only)

```env
LLM_PROVIDER_CHAIN=groq
LLM_COOLDOWN_SEC=4.0
LLM_SOFT_DAILY_CALLS=80
MAX_PLAN_STEPS=4
MAX_TOKENS_FULL_TIER=768
GROQ_DEFER_HEAVY_ON_BUDGET=true
NOTEBOOK_MAX_CHARS=1500
```

- **`LLM_SOFT_DAILY_CALLS=0`** — отключить учёт (только cooldown).
- После апгрейда VPS / второго провайдера — поднять лимиты или добавить `gemini` в цепочку.

## Приоритет работ (под текущие ресурсы)

1. Neon + Redis на VPS (если ещё нет).
2. Фаза 0 roadmap: confirm, E2E, `/journal`.
3. Блокнот + бюджет LLM (этот документ).
4. Интеграции calendar/GitHub — **stub OK** без тяжёлых зависимостей.
5. Firecracker, MCP hub, eval harness — **после** стабильного solo-использования.

## Когда брать VPS получше

- Нужен локальный embedding / Ollama.
- Постоянно >80 LLM-вызовов в день на одного пользователя.
- Docker-sandbox для `run_code` на каждый запрос.

До этого: внешняя память + короткие планы + один провайдер Groq.
