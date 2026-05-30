# Деплой на Timeweb Cloud VPS (Амстердам)

> **Production (FirstByte FI):** см. [`FIRSTBYTE_VPS.md`](FIRSTBYTE_VPS.md) — IP `91.186.221.32`, `/opt/agentsTG`.

## 1. Покупка VPS

1. Перейди на https://cloud.timeweb.com/
2. Зарегистрируйся (российский номер подходит)
3. Пополни баланс (350–400₽ хватит на месяц)
4. Создай сервер:
   - **Тип**: Cloud VPS (не выделенный сервер!)
   - **Локация**: Amsterdam 🇳🇱 (важно!)
   - **ОС**: Ubuntu 22.04 LTS
   - **Конфиг**: 1 CPU, 1GB RAM, 25GB SSD (минимальный)
   - **SSH ключ**: создай в PowerShell: `ssh-keygen -t ed25519`
   - Скопируй содержимое `~/.ssh/id_ed25519.pub` в поле SSH-ключ

## 2. Подключение по SSH

```powershell
# В PowerShell:
ssh ubuntu@IP_АДРЕС_СЕРВЕРА
```

## 3. Установка ботов

На сервере выполни:

```bash
# Обновление системы
sudo apt update && sudo apt install -y git python3-poetry

# Клонирование репозитория (замени на свой)
cd /opt
sudo git clone https://github.com/ТВОЙ_USERNAME/agentsTG.git
sudo chown -R $USER:$USER agentsTG
cd agentsTG

# Установка зависимостей
poetry install --no-root

# Создание .env файла
sudo nano .env
```

Вставь в `.env` все токены (Ctrl+O, Enter, Ctrl+X для сохранения):

```
BOT_TOKEN_ORCHESTRATOR=your_orchestrator_bot_token
BOT_TOKEN_PA=your_pa_bot_token
BOT_TOKEN_CODER=your_coder_bot_token
BOT_TOKEN_RESEARCH=your_research_bot_token
BOT_TOKEN_SECURITY=your_security_bot_token
BOT_TOKEN_BUSINESS=your_business_bot_token
BOT_TOKEN_MARKETING=your_marketing_bot_token
GROUP_CHAT_ID=your_group_chat_id
QWEN_API_KEY=your_qwen_api_key_here
```

### Gemini API (recommended primary LLM)

1. Open https://aistudio.google.com/apikey
2. Create API key (no credit card on free tier)
3. Add to `.env`:

```
GEMINI_API_KEY=your_key_here
LLM_PROVIDER_CHAIN=gemini,groq
GROQ_API_KEY=your_groq_key_here
```

Gemini free tier offers much higher TPM than Groq (better for long system prompts + tools).

## 4. Systemd сервис (автозапуск)

```bash
# Копируем service файл
sudo cp deploy/agents-tg.service /etc/systemd/system/
sudo systemctl daemon-reload

# Запускаем и включаем автозапуск
sudo systemctl enable --now agents-tg

# Проверка статуса
sudo systemctl status agents-tg

# Логи в реальном времени
sudo journalctl -u agents-tg -f
```

## 5. Управление ботами

```bash
# Проверить работают ли
sudo systemctl status agents-tg

# Перезапустить (после обновления кода)
sudo systemctl restart agents-tg

# Остановить
sudo systemctl stop agents-tg

# Логи
sudo journalctl -u agents-tg -n 100
```

## 6. Обновление кода

```bash
cd /opt/agentsTG
git pull
sudo systemctl restart agents-tg
```

## 7. Мониторинг

```bash
# Загрузка CPU/RAM
htop

# Свободное место
df -h

# Сетевые соединения ботов
sudo ss -tuln | grep 443
```

## Типичные проблемы

### Боты не стартуют
```bash
# Проверь логи
sudo journalctl -u agents-tg -n 50

# Проверь .env
sudo cat /opt/agentsTG/.env | head -5
```

### Нет интернета с сервера
```bash
ping api.telegram.org
# Должен пинговаться (если нет — пиши в поддержку Timeweb)
```

### Закончилось место
```bash
df -h
# Если /opt заполнен — чистим логи:
sudo journalctl --vacuum-time=3d
```

## Проверка в Telegram

Через 2 минуты после запуска:
- Напиши `@egor_orchestrator_bot` /start
- Напиши в группу: `@egor_orchestrator_bot` привет команде!

Если бот отвечает — всё работает 24/7!
