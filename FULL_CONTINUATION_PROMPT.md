# FULL CONTEXT FOR CURSOR — Multi-Agent Telegram AI System

> Этот файл — полный дамп контекста проекта для передачи между AI-агентами (Cline → Cursor).
> Создан: 2026-05-26 18:45 MSK

---

## 1. ЧТО МЫ СТРОИМ

**Мультиагентная система AI-помощников в Telegram.**

Пользователь общается с 6 специализированными AI-агентами в одном чате.
У каждого агента — своя личность (SOUL.md), свои инструменты, память, интернет-доступ.
Они могут работать как по одному (личная переписка с каждым), так и командой над сложными задачами.

---

## 2. ТЕКУЩАЯ ПРОБЛЕМА (что не так)

Сейчас архитектура **сломана**:
- `orchestrator.py` возвращает ОДНУ строку → бот отправляет одно сообщение
- Пользователь НЕ видит работу разных агентов — всё склеивается в один ответ
- Есть мёртвый код: `coordinator.py`, `specialists.py` с устаревшими классами
- `personal_assistant.py` грузит неверный SOUL-файл
- Mem0 падает без API ключа
- Путаница в названиях агентов (sports_analyst vs research_analyst)

---

## 3. ЦЕЛЬ

### 3.1. Архитектура (как должно быть)

```
Пользователь пишет в чат Telegram
       │
       ▼
┌─────────────────────────────────────────────────┐
│                🧭 КООРДИНАТОР                     │
│  Анализирует запрос → составляет план            │
│  → распределяет задачи между агентами            │
│  → контролирует выполнение → сбор результата     │
└─────────────────────────────────────────────────┘
       │
       ├──── 🎯 Личный Ассистент (Эльза)
       │     Задачи + планирование + календарь + заметки + поиск
       │
       ├──── 👨‍💻 Кодер (Руслан)
       │     Код, ревью, репозитории, CI/CD, DevOps
       │
       ├──── 📈 Финансы (Ульяна)
       │     Расходы, доходы, налоги, фин. аналитика
       │
       ├──── 📢 Маркетолог (Саша)
       │     Автономный мониторинг трендов, поиск клиентов/лидов,
       │     анализ конкурентов, контент-план
       │
       ├──── 🔗 Интегратор (Тася)
       │     Внешние API, погода, Obsidian, Git, бронирования
       │
       └──── 🧭 Координатор (Николай)
             Делегирование, эскалация, контроль качества
```

### 3.2. Как выглядят сообщения в чате

```
Пользователь: "Нужно запустить лендинг за неделю"

🧭 Координатор:
📋 План действий:
1. Кодер — оценить фронтенд фреймворк и подготовить шаблон
2. Маркетолог — проанализировать конкурентов и УТП
3. Финансы — прикинуть бюджет на хостинг и домен

---

👨‍💻 Кодер (Руслан):
Выбрал Next.js. Шаблон готов через 2 часа. 
Нужен хостинг: Vercel (бесплатно для старта) или свой сервер.
Репозиторий: [ссылка]

---

📢 Маркетолог (Саша):
Проанализировал топ-5 конкурентов:
1. ... 
2. ...
Рекомендую УТП: ...
Начал мониторинг в фоне, отчитаюсь при изменениях.

---

🧭 Координатор:
Все задачи выполняются. Ориентировочный срок: 5 дней.
Что-то ещё, пользователь?
```

### 3.3. Личная переписка с агентом

Пользователь может написать **конкретному агенту напрямую**:
- `/coder` → дальше только Руслан отвечает
- `/marketer` → дальше только Саша
- И т.д.

Команда `/team` или без префикса → подключается Координатор.

---

## 4. ТЕХНИЧЕСКИЙ СТЕК

| Компонент | Технология |
|-----------|-----------|
| Runtime | Python 3.11+ (сейчас 3.13) |
| Telegram | aiogram 3.x |
| Оркестрация | LangGraph (StateGraph) |
| AI | Qwen 2.5-72B-Instruct через HuggingFace API |
| Память | Mem0 (AI memory) |
| Поиск | DuckDuckGo + Trafilatura |
| База данных | PostgreSQL + SQLAlchemy async |
| Миграции | Alembic |
| Кэш | Redis (планируется) |
| Деплой | Railway.app / Render.com |
| Линтеры | black, isort, flake8 |
| Тесты | pytest |

---

## 5. СУЩЕСТВУЮЩАЯ СТРУКТУРА ФАЙЛОВ

```
agentsTG/
├── src/
│   ├── main.py                         # Точка входа
│   ├── agents_tg/
│   │   ├── __init__.py
│   │   ├── bot/
│   │   │   └── __init__.py             # Telegram handlers (aiogram router)
│   │   ├── agents/
│   │   │   ├── coordinator.py          # ⚠️ МЁРТВЫЙ — удалить
│   │   │   ├── orchestrator.py         # ⚠️ НУЖЕН РЕФАКТОРИНГ
│   │   │   ├── personal_assistant.py   # ⚠️ НУЖЕН ФИКС (не тот SOUL)
│   │   │   ├── specialists.py          # ⚠️ РАЗДЕЛИТЬ НА 6 ФАЙЛОВ
│   │   │   └── souls/                  # ✅ SOUL-файлы (14 шт)
│   │   │       ├── coordinator_soul.md
│   │   │       ├── coder_soul.md
│   │   │       ├── planner_soul.md
│   │   │       ├── assistant_soul.md
│   │   │       ├── finance_soul.md
│   │   │       ├── integrator_soul.md
│   │   │       ├── tutor_soul.md
│   │   │       ├── marketing.md
│   │   │       ├── sports_analyst.md
│   │   │       ├── security_ai.md
│   │   │       ├── business_manager.md
│   │   │       ├── general.md
│   │   │       ├── orchestrator.md
│   │   │       └── personal_assistant.md
│   │   ├── services/
│   │   │   ├── qwen_client.py          # Qwen API клиент
│   │   │   ├── memory_service.py       # Mem0 сервис
│   │   │   └── ...
│   │   ├── db/
│   │   │   ├── models.py               # SQLAlchemy модели
│   │   │   ├── session.py              # Async сессия
│   │   │   └── migrations/             # Alembic
│   │   └── utils/
│   │       ├── internet.py             # DuckDuckGo + Trafilatura
│   │       └── git_sync.py             # Git для Obsidian
│   └── database/
│   └── integrations/
├── tests/
│   └── test_settings.py                # 4 теста
├── docs/
│   ├── implementation-notes.md         # Журнал решений
│   ├── PROJECT_VERIFICATION.md         # Команды проверки
│   └── ...
├── pyproject.toml                      # Poetry config
├── .env.example
├── .flake8
├── .gitignore
└── FULL_CONTINUATION_PROMPT.md         ← ЭТОТ ФАЙЛ
```

---

## 6. КЛЮЧЕВЫЕ ФАЙЛЫ ДЛЯ ИЗУЧЕНИЯ

Перед началом работы прочитай эти файлы (порядок важен):

1. **PROJECT_PROMPT.md** — архитектура, промпты, roadmap
2. **PROJECT_STATE.json** — текущее состояние задач
3. **PROGRESS.md** — что уже сделано по этапам
4. **docs/implementation-notes.md** — журнал всех решений и tradeoffs
5. **docs/PROJECT_VERIFICATION.md** — команды проверки (black, isort, flake8, pytest)
6. **src/agents_tg/agents/orchestrator.py** — главный файл для рефакторинга
7. **src/agents_tg/agents/specialists.py** — класс ToolEnabledAgent (база для агентов)
8. **src/agents_tg/bot/__init__.py** — Telegram handlers
9. **src/agents_tg/services/qwen_client.py** — как ходим к AI
10. **src/agents_tg/services/memory_service.py** — Mem0 (нужен graceful fallback)

---

## 7. ЧТО НУЖНО СДЕЛАТЬ (план рефакторинга)

### Этап 1: Чистая архитектура агентов
- [ ] Удалить `coordinator.py` (мёртвый)
- [ ] Удалить `orchestrator.py` (будет переписан)
- [ ] Создать `agents/orchestrator.py` — новый с методами send_message
- [ ] Создать 6 файлов агентов в `agents/`:
  - `coordinator_agent.py`  — 🧭 Координатор
  - `coder_agent.py`        — 👨‍💻 Кодер
  - `finance_agent.py`      — 📈 Финансы
  - `marketer_agent.py`     — 📢 Маркетолог
  - `integrator_agent.py`   — 🔗 Интегратор
  - `assistant_agent.py`    — 🎯 Личный Ассистент
- [ ] Каждый наследует `ToolEnabledAgent` из `specialists.py`
- [ ] У каждого свой SOUL.md, свои tools, свой output contract
- [ ] `personal_assistant.py` — исправить SOUL на assistant_soul.md

### Этап 2: Telegram — отдельные сообщения от агентов
- [ ] `orchestrator.process()` принимает `(message, user_id, bot, chat_id)`
- [ ] Координатор отправляет план → `bot.send_message()`
- [ ] Каждый агент отправляет свой ответ → `bot.send_message()`
- [ ] `/coder`, `/finance`, etc. — команды для личного обращения к агенту
- [ ] `/team` — командный режим через Координатора

### Этап 3: Manus-like фичи
- [ ] Agent Journal — каждый агент ведёт дневник своих действий (в память)
- [ ] Sub-agent creation — агент может породить временного под-агента
- [ ] Step-by-step видимость — каждый шаг плана → отдельное сообщение
- [ ] Tool sandbox — у каждого агента свой набор инструментов
- [ ] Confirmation before action — перед destructive действиями

### Этап 4: Маркетолог — автономный режим
- [ ] Фоновый мониторинг трендов по расписанию (периодическая задача)
- [ ] Автоматическое уведомление о новых лидах/клиентах
- [ ] Анализ конкурентов по запросу

### Этап 5: Стабилизация
- [ ] Mem0 — graceful fallback без API ключа
- [ ] Тесты для каждого агента (smoke tests)
- [ ] `npm run verify` — зелёный
- [ ] Обновить PROJECT_STATE.json, PROGRESS.md, docs/implementation-notes.md

---

## 8. ПРИНЦИПЫ РАБОТЫ

1. **Простота > Сложность** — не раздувай архитектуру
2. **Type hints везде** — никакой `Any` без необходимости
3. **Async/await** — всё I/O асинхронное
4. **Single Responsibility** — один файл = один агент
5. **Не трогай файлы вне scope задачи**
6. **После правок → verify**: `black . && isort . && flake8 src/ tests/ && pytest tests/ -v`
7. **Обновляй docs/implementation-notes.md** — каждое решение и tradeoff
8. **Не используй `claw` CLI** без явного запроса

---

## 9. ВДОХНОВЕНИЕ: Manus AI + Open Claw

### Из Manus (https://manus.im):
- **Autonomous task execution** — агент сам решает КОГДА и КАК выполнять шаги
- **Sub-agent spawning** — для подзадач создаются временные агенты
- **Transparent process** — пользователь видит каждый шаг выполнения
- **Agent journal** — каждый агент ведёт лог своих действий и решений
- **Tool integration** — браузер, код, файлы, поиск — всё в одном

### Из Open Claw (https://github.com/ultraworkers/claw-code):
- **Контракт на output** — чёткий формат ответа для каждого типа задачи
- **Confirmation gates** — перед destructive операциями
- **Structured thinking** — "под капотом" агент показывает свой мыслительный процесс
- **File operations** — чтение, создание, редактирование файлов

---

## 10. ТЕХНИЧЕСКИЕ ЗАМЕТКИ

- **Python 3.13** — совместимость с flake8 проблемная, нужна версия `<7.1`
- **Poetry sync** — вместо `poetry install` используй `poetry sync`
- **Qwen** — температура 0.1-0.3 для агентов, 0.7 для креатива
- **Mem0** — если нет API ключа, сервис должен возвращать пустой результат, не падать
- **База** — PostgreSQL пока недоступен локально, in-memory хранилище для MVP

---

## 11. КОНТАКТНАЯ ИНФОРМАЦИЯ

Если что-то неясно — НЕ УГАДЫВАЙ. Напиши список вопросов пользователю.
Лучше спросить 1 раз, чем сделать неправильно и переделывать.

---

*Конец промпта. Удачи, Cursor! 🚀*