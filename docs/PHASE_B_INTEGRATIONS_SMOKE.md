---
summary: Prod smoke prompts для calendar, GitHub, research cite; CalDAV write defer
read_when: Phase B integrations sign-off в E2E_SIGNOFF_TEMPLATE
---

# Phase B — Integration smoke (manual Telegram)

CalDAV **write** — **deferred** (read/stub only per `INTEGRATIONS.md`). Не блокер Phase A.

## Calendar (Эльза)

**Сообщение:** `Что в календаре на завтра?`

**Pass:** ответ без traceback; stub или CalDAV read; запись в JOURNAL при успехе.

## GitHub (Руслан)

**Сообщение:** `Покажи открытые issues в репозитории agentsTG`

**Pass:** список issues или явное «нет GITHUB_TOKEN» без падения.

## Research cite (Ульяна)

**Сообщение:** `Кратко: что нового в Python 3.13 — со ссылками`

**Pass:** HTML `<a href="...">` citations в ответе (см. eval `research_citations_html`).

## Отметка

Заполнить таблицу «MVP integration smoke» в [`E2E_SIGNOFF_TEMPLATE.md`](E2E_SIGNOFF_TEMPLATE.md).
