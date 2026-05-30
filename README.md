# 🤖 AI Agents Telegram Assistant

> Интеллектуальная мультиагентная система для автоматизации личной жизни через Telegram

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-in%20development-yellow.svg)]()

---

## 📋 Описание

AI Agents Telegram Assistant — это мультиагентный «офис» на базе искусственного интеллекта. У тебя есть Оркестратор и 6 специализированных агентов, к которым можно обратиться лично или собрать их в общий «военный совет»:

- 📅 **Личный помощник** — календарь, задачи, заметки (Obsidian), лёгкий личный бюджет
- 🔎 **Research / Intel** — поиск репозиториев, best practices, конкурентов, технических решений
- 🛡️ **Security & AI** — безопасность кода и архитектуры, устойчивость LLM
- 💼 **Business & PM** — стратегии, MVP-планы, приоритизация и риски
- 📈 **Marketing & Growth** — позиционирование, контент-планы, каналы роста
- 🧭 **Оркестратор** — строит план из шагов и подключает нужных специалистов

### Ключевые особенности

✨ **Мультиагентная архитектура** - специализированные AI агенты для разных задач  
🤝 **Взаимодействие агентов** - агенты общаются между собой для решения комплексных задач  
🧠 **Умный координатор** - автоматическая маршрутизация запросов к нужным агентам  
💾 **Сохранение контекста** - система помнит историю и предпочтения  
🔐 **Безопасность** - шифрование данных, приватность  
☁️ **24/7 доступность** - работает в облаке без необходимости держать компьютер включённым

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────┐
│         Orchestrator Agent              │
│      (Планирование и супервизия)        │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴───────────────────────────────────────┐
        │                 │                │              │
┌───────▼────────┐ ┌──────▼────────┐ ┌─────▼───────┐ ┌────▼─────┐
│ Personal Asst  │ │ Research      │ │ Security AI │ │ Business │
│ (Obsidian,     │ │ (Repos, Docs, │ │ (LLM Sec,   │ │ (Projects,│
│  Calendar)     │ │  Market)      │ │  Coding)    │ │  CRM)     │
└────────────────┘ └───────────────┘ └─────────────┘ └──────────┘
        │
┌───────▼────────┐
│ Marketing      │
│ (Growth, Ads)  │
└────────────────┘
```

### Агенты

1. **Orchestrator** — главный дирижёр, анализирует запросы и строит план из шагов.
2. **Personal Assistant** — календарь, задачи, заметки и личный быт.
3. **Research / Intel** — ресерч по репозиториям, архитектурам, рынку и конкурентам.
4. **Security & AI Researcher** — безопасность кода и LLM.
5. **Business & Project Manager** — проекты, продукты, дорожные карты.
6. **Marketing & Growth** — маркетинг, контент, рост.

---

## 🛠️ Технологический стек

### Backend
- **Python 3.11+** - основной язык
- **aiogram 3.x** - Telegram Bot framework
- **FastAPI** - REST API и webhooks
- **SQLAlchemy 2.0** - ORM
- **Alembic** - миграции БД

### База данных
- **PostgreSQL** - основное хранилище
- **Redis** - кэш, очереди, сессии

### AI
- **Qwen 2.5** — основная модель через бесплатные публичные эндпоинты (HuggingFace Inference; возможен fallback на OpenRouter free‑tier).
- **Единый клиент `qwen_client`** — общая прослойка для всех агентов.

### Инфраструктура
- **Python 3.11+** — основной runtime
- **Render.com / Railway / VPS** — возможные варианты бесплатного/дешёвого хостинга
- **Docker** — контейнеризация приложения

---

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- PostgreSQL 14+ (для продакшена, локально можно обходиться без БД)
- Redis 7+ (кэш, очереди — опционально)
- Telegram Bot Token
- Qwen API Key (HuggingFace / другой бесплатный провайдер)

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/agentsTG.git
cd agentsTG

# Установка зависимостей
poetry install

# Или через pip
pip install -r requirements.txt

# Копирование конфигурации
cp .env.example .env

# Редактирование .env файла
nano .env
```

### Конфигурация

Создайте `.env` файл со следующими переменными (минимум):

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Qwen API (HuggingFace / др. бесплатный провайдер)
QWEN_API_KEY=your_qwen_api_key_here
QWEN_MODEL=qwen2.5-72b-instruct
QWEN_API_BASE=https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agentsdb

# Redis
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=True

# Security
SECRET_KEY=your_secret_key_here
```

### Запуск

```bash
# (опционально) Применение миграций
alembic upgrade head

# Запуск Telegram-бота (polling mode)
poetry run python -m src.main
```

### Docker (опционально)

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

---

## 📖 Использование

### Основные команды

- `/start` — приветствие и список доступных агентов
- `/help` — краткая справка
- `/menu` — inline-меню с агентами
- `/team` — командный режим (Оркестратор строит план и подключает агентов)
- `/pa` — личный диалог с Личным помощником
- `/coder` — диалог с Coder/Architect (планируется)
- `/research` — диалог с ресерчером
- `/biz` — диалог с Business & PM
- `/mkt` — диалог с Marketing & Growth
- `/sec` — диалог с Security & AI

### Примеры использования

**Планирование:**
```
👤 Создай встречу завтра в 15:00 с Иваном
🤖 Создал встречу "Встреча с Иваном" на 24 мая в 15:00
```

**Финансы:**
```
👤 Потратил 500 рублей на обед
🤖 Записал расход 500₽ в категорию "Продукты". 
   Осталось 2500₽ из бюджета на месяц.
```

**Заметки:**
```
👤 Запомни: пароль от WiFi - MySecurePass123
🤖 Сохранил заметку с тегом #пароли
```

**Интеграции:**
```
👤 Забронируй столик в ресторане на двоих на субботу
🤖 Ищу доступные рестораны... Нашёл 5 вариантов.
   Какой предпочитаешь?
```

---

## 📁 Структура проекта

```
agentsTG/
├── src/
│   ├── agents_tg/
│   │   ├── agents/          # Реализация агентов и оркестратора
│   │   │   ├── souls/       # SOUL.md для каждого агента
│   │   │   ├── orchestrator.py
│   │   │   ├── specialists.py
│   │   ├── bot/             # Telegram-бот (aiogram)
│   │   ├── config/          # Настройки (pydantic-settings)
│   │   ├── db/              # SQLAlchemy модели, миграции Alembic
│   │   ├── services/        # Клиенты LLM, память, интеграции
│   │   └── utils/           # Утилиты (поиск, git-синхронизация и т.п.)
│   └── main.py              # Точка входа для бота
├── tests/                   # Тесты
├── docs/                    # Документация (PROMPT, PROGRESS, VERIFICATION)
├── Dockerfile
├── alembic.ini
├── pyproject.toml           # Poetry конфигурация
├── .env.example
└── README.md
```

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest tests/ -v

# С покрытием
pytest tests/ -v --cov=src --cov-report=html

# Конкретный файл
pytest tests/test_llm_client.py -v
```

---

## 📊 Разработка

### Настройка окружения разработки

```bash
# Установка dev-зависимостей
poetry install --with dev

# Pre-commit hooks
pre-commit install

# Форматирование кода
black .
isort .

# Линтинг
flake8 .
mypy .

# Проверка безопасности
bandit -r src/
```

### Workflow

1. Создать ветку: `git checkout -b feature/new-feature`
2. Внести изменения
3. Запустить тесты: `pytest`
4. Закоммитить: `git commit -m "feat: add new feature"`
5. Создать PR

### Формат коммитов

Используем [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - новая функциональность
- `fix:` - исправление бага
- `docs:` - документация
- `style:` - форматирование
- `refactor:` - рефакторинг
- `test:` - тесты
- `chore:` - рутинные задачи

---

## 🚢 Деплой

### VPS FirstByte (production)

См. [`deploy/FIRSTBYTE_VPS.md`](deploy/FIRSTBYTE_VPS.md) — IP `91.186.221.32`, `/opt/agentsTG`.

Обязательно в `.env`:

```env
GEMINI_API_KEY=...          # https://aistudio.google.com/apikey (free)
LLM_PROVIDER_CHAIN=gemini,groq
GROQ_API_KEY=...            # fallback
```

### Railway.app / Render

1. Создать аккаунт на [Railway.app](https://railway.app/)
2. Подключить GitHub репозиторий
3. Добавить PostgreSQL и Redis сервисы
4. Настроить переменные окружения
5. Деплой произойдёт автоматически

### Ручной деплой

```bash
# Сборка Docker образа
docker build -t agentsbot .

# Запуск
docker run -d \
  --name agentsbot \
  --env-file .env \
  -p 8000:8000 \
  agentsbot
```

---

## 📈 Roadmap

### v0.1 (Текущая версия) - MVP
- [x] Архитектура и документация
- [ ] Базовый Telegram bot
- [ ] Coordinator Agent
- [ ] Planner Agent (базовый)
- [ ] Finance Agent (базовый)

### v0.2 - Расширенный функционал
- [ ] Notes Agent
- [ ] Integration Agent
- [ ] Google Calendar интеграция
- [ ] Веб-интерфейс для аналитики

### v0.3 - Улучшения
- [ ] Голосовые сообщения
- [ ] ML для категоризации расходов
- [ ] Банковские API
- [ ] Сервисы бронирования

### v1.0 - Production Ready
- [ ] Полное покрытие тестами
- [ ] Документация API
- [ ] Мониторинг и алерты
- [ ] Масштабирование

---

## 🤝 Вклад в проект

Мы приветствуем вклад в проект! Пожалуйста:

1. Форкните репозиторий
2. Создайте ветку для вашей фичи
3. Напишите тесты
4. Убедитесь что все тесты проходят
5. Создайте Pull Request

См. [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.

---

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. [LICENSE](LICENSE) файл для деталей.

---

## 👥 Авторы

- **Ваше имя** - *Initial work* - [YourGitHub](https://github.com/yourusername)

---

## 🙏 Благодарности

- [aiogram](https://github.com/aiogram/aiogram) - отличный Telegram Bot framework
- [Alibaba Cloud](https://www.alibabacloud.com/) - за бесплатный доступ к Qwen API
- [Railway.app](https://railway.app/) - за удобный хостинг

---

## 📞 Контакты

- Telegram: [@yourusername](https://t.me/yourusername)
- Email: your.email@example.com
- GitHub Issues: [Issues](https://github.com/yourusername/agentsTG/issues)

---

## 📚 Дополнительная документация

- [PROJECT_PROMPT.md](docs/PROJECT_PROMPT.md) - Детальное описание проекта и промпты агентов
- [PROGRESS.md](docs/PROGRESS.md) - Текущий прогресс разработки
- [API.md](docs/API.md) - API документация
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Инструкции по деплою

---

**Статус проекта:** 🚧 В активной разработке

**Последнее обновление:** 2026-05-23
