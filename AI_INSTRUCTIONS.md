# Инструкции для AI при работе над проектом

> Этот документ описывает, как AI должен работать с проектом AI Agents Telegram Assistant

---

## 🎯 Цель и контекст

Вы работаете над мультиагентной системой для Telegram, которая помогает пользователю автоматизировать личную жизнь. Проект находится в начальной стадии разработки.

**Важные ограничения:**
- Пользователь работает на ноутбуке - локальные тяжёлые модели не подходят
- Нужен бесплатный хостинг 24/7
- Работа ведётся в Harvi Code с ограниченными лимитами
- Важна автономность и сохранение контекста

---

## 📋 Обязательный workflow

### 1. Перед началом работы

**ВСЕГДА** читайте эти файлы:

```bash
1. PROJECT_STATE.json - текущее состояние проекта
2. PROGRESS.md - что сделано, что в процессе
3. PROJECT_PROMPT.md - архитектура и промпты агентов
```

**Анализируйте:**
- Какая фаза проекта сейчас?
- Что уже реализовано?
- Какие задачи в процессе?
- Есть ли блокеры?

### 2. Планирование задачи

**Перед реализацией:**
1. Убедитесь, что задача соответствует архитектуре
2. Проверьте зависимости (что должно быть готово до этого)
3. Определите scope (что входит, что не входит)
4. Оцените риски

**Если задача неясна:**
- Задайте уточняющие вопросы
- Предложите варианты реализации
- Укажите на возможные проблемы

### 3. Реализация

**Правила кодирования:**

```python
# ✅ ХОРОШО: Чистый, простой код
class PlannerAgent:
    """Агент для планирования и управления задачами."""
    
    async def create_event(self, title: str, datetime: datetime) -> Event:
        """Создаёт событие в календаре."""
        event = Event(title=title, datetime=datetime)
        await self.db.save(event)
        return event

# ❌ ПЛОХО: Излишняя сложность
class AbstractPlannerAgentFactoryInterface:
    """Abstract factory for creating planner agent instances..."""
    # Не нужны лишние абстракции!
```

**Принципы:**
- Простота > сложность
- Читаемость > краткость
- Явное > неявное
- Тестируемость обязательна

**Структура файлов:**
```python
# Каждый файл должен иметь:
"""
Модуль для работы с X.

Описание что делает модуль.
"""

from typing import ...  # Импорты стандартной библиотеки
import ...

from third_party import ...  # Сторонние библиотеки

from src.module import ...  # Локальные импорты

# Код модуля
```

### 4. Тестирование

**Перед коммитом ОБЯЗАТЕЛЬНО:**

```bash
# 1. Форматирование
black .
isort .

# 2. Линтинг
flake8 .
mypy .

# 3. Тесты
pytest tests/ -v

# 4. Безопасность
bandit -r src/
```

**Пишите тесты для:**
- Всех публичных методов
- Граничных случаев
- Обработки ошибок
- Интеграций с внешними API

### 5. Документация

**Обновляйте после каждой задачи:**

```json
// PROJECT_STATE.json
{
  "completed_tasks": [
    "Новая выполненная задача"  // ← Добавить
  ],
  "current_tasks": [
    "Задача в процессе"
  ]
}
```

```markdown
<!-- PROGRESS.md -->
## ✅ Выполнено

### Этап X: Название
- [x] Выполненная задача  ← Отметить
- [ ] Следующая задача
```

### 6. Коммит

**Формат коммита:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Примеры:**
```bash
# Новая функция
git commit -m "feat(planner): добавлен метод create_event

- Реализован базовый функционал создания событий
- Добавлены тесты
- Обновлена документация

Closes #5"

# Исправление бага
git commit -m "fix(finance): исправлена категоризация транзакций

Категория 'Продукты' не определялась для чеков из магазинов.
Добавлена проверка по ключевым словам.

Fixes #12"

# Документация
git commit -m "docs: обновлён README с примерами использования"
```

---

## 🤖 Специфика работы с агентами

### Создание нового агента

**Шаблон:**

```python
"""
Модуль с реализацией [Название] Agent.
"""

from typing import Optional, List
from datetime import datetime

from src.agents.base import BaseAgent
from src.database.models import User
from src.utils.ai import AIClient


class [Name]Agent(BaseAgent):
    """
    [Название] Agent - [краткое описание роли].
    
    Ответственность:
    - Функция 1
    - Функция 2
    - Функция 3
    """
    
    def __init__(self, ai_client: AIClient):
        """Инициализация агента."""
        super().__init__(
            name="[name]",
            role="[описание роли]",
            ai_client=ai_client
        )
        self.system_prompt = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Загружает системный промпт агента."""
        return """
        Ты - [Name] Agent, [роль].
        
        Твои функции:
        1. ...
        2. ...
        
        Правила:
        - ...
        - ...
        """
    
    async def process(self, user_input: str, context: dict) -> dict:
        """
        Обрабатывает запрос пользователя.
        
        Args:
            user_input: Текст запроса
            context: Контекст диалога
            
        Returns:
            Результат обработки
        """
        # Реализация
        pass
    
    # Специфичные методы агента
    async def specific_method(self, param: str) -> str:
        """Описание метода."""
        pass
```

### Промпты агентов

**Структура промпта:**

```python
SYSTEM_PROMPT = """
Ты - [Название] Agent, [роль в системе].

Твоя задача:
1. [Основная задача]
2. [Дополнительная задача]

Доступные инструменты:
- tool_name(param1, param2): описание
- another_tool(param): описание

Правила:
- Правило 1
- Правило 2
- Правило 3

Формат ответа:
{
  "action": "название_действия",
  "params": {...},
  "response": "ответ пользователю"
}

Стиль общения: [описание стиля]
"""
```

### Function calling

**Определение функций:**

```python
FUNCTIONS = [
    {
        "name": "create_event",
        "description": "Создаёт событие в календаре",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Название события"
                },
                "datetime": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Дата и время в ISO формате"
                },
                "duration": {
                    "type": "integer",
                    "description": "Длительность в минутах"
                }
            },
            "required": ["title", "datetime"]
        }
    }
]
```

**Обработка вызовов:**

```python
async def handle_function_call(self, function_name: str, arguments: dict):
    """Обрабатывает вызов функции от AI."""
    
    if function_name == "create_event":
        return await self.create_event(**arguments)
    elif function_name == "create_task":
        return await self.create_task(**arguments)
    else:
        raise ValueError(f"Unknown function: {function_name}")
```

---

## 🔧 Работа с базой данных

### Создание модели

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database.base import Base


class Event(Base):
    """Модель события в календаре."""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    datetime = Column(DateTime, nullable=False)
    duration = Column(Integer, default=60)  # минуты
    
    # Связи
    user = relationship("User", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}')>"
```

### Создание миграции

```bash
# Автогенерация
alembic revision --autogenerate -m "add events table"

# Ручная миграция
alembic revision -m "add custom index"
```

### CRUD операции

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class EventCRUD:
    """CRUD операции для событий."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, **kwargs) -> Event:
        """Создаёт событие."""
        event = Event(**kwargs)
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event
    
    async def get(self, event_id: int) -> Optional[Event]:
        """Получает событие по ID."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_user(self, user_id: int) -> List[Event]:
        """Получает все события пользователя."""
        result = await self.session.execute(
            select(Event)
            .where(Event.user_id == user_id)
            .order_by(Event.datetime)
        )
        return result.scalars().all()
```

---

## 🔌 Интеграции с внешними API

### Базовый клиент

```python
import httpx
from typing import Optional


class BaseAPIClient:
    """Базовый класс для API клиентов."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> dict:
        """Выполняет HTTP запрос."""
        try:
            response = await self.client.request(
                method,
                endpoint,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            # Логирование и обработка ошибок
            raise
    
    async def close(self):
        """Закрывает соединение."""
        await self.client.aclose()
```

### Пример интеграции

```python
class GoogleCalendarClient(BaseAPIClient):
    """Клиент для Google Calendar API."""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://www.googleapis.com/calendar/v3"
        )
    
    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start: datetime,
        end: datetime
    ) -> dict:
        """Создаёт событие в календаре."""
        event = {
            "summary": title,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()}
        }
        return await self._request(
            "POST",
            f"/calendars/{calendar_id}/events",
            json=event
        )
```

---

## 🧪 Тестирование

### Unit тесты

```python
import pytest
from datetime import datetime
from src.agents.planner import PlannerAgent


@pytest.fixture
def planner_agent():
    """Фикстура для PlannerAgent."""
    return PlannerAgent(ai_client=MockAIClient())


@pytest.mark.asyncio
async def test_create_event(planner_agent):
    """Тест создания события."""
    # Arrange
    title = "Встреча"
    dt = datetime(2026, 5, 24, 15, 0)
    
    # Act
    event = await planner_agent.create_event(title, dt)
    
    # Assert
    assert event.title == title
    assert event.datetime == dt


@pytest.mark.asyncio
async def test_create_event_invalid_date(planner_agent):
    """Тест создания события с невалидной датой."""
    with pytest.raises(ValueError):
        await planner_agent.create_event("Test", "invalid")
```

### Integration тесты

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_delegates_to_planner(
    coordinator,
    planner,
    db_session
):
    """Тест делегирования от координатора к планировщику."""
    # Arrange
    user_input = "Создай встречу завтра в 15:00"
    
    # Act
    result = await coordinator.process(user_input)
    
    # Assert
    assert result["agent_used"] == "planner"
    assert "встреча" in result["response"].lower()
    
    # Проверяем что событие создано в БД
    events = await db_session.query(Event).all()
    assert len(events) == 1
```

---

## 📊 Логирование и мониторинг

### Настройка логирования

```python
import logging
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlannerAgent:
    async def create_event(self, title: str, datetime: datetime):
        logger.info(
            "Creating event",
            extra={
                "title": title,
                "datetime": datetime.isoformat(),
                "agent": "planner"
            }
        )
        
        try:
            event = await self._create_event(title, datetime)
            logger.info(
                "Event created successfully",
                extra={"event_id": event.id}
            )
            return event
        except Exception as e:
            logger.error(
                "Failed to create event",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
```

### Метрики

```python
from prometheus_client import Counter, Histogram

# Счётчики
events_created = Counter(
    "events_created_total",
    "Total number of events created"
)

# Гистограммы
event_creation_duration = Histogram(
    "event_creation_duration_seconds",
    "Time spent creating events"
)


@event_creation_duration.time()
async def create_event(self, title: str, datetime: datetime):
    event = await self._create_event(title, datetime)
    events_created.inc()
    return event
```

---

## 🚨 Обработка ошибок

### Иерархия исключений

```python
class AgentError(Exception):
    """Базовое исключение для агентов."""
    pass


class AgentNotFoundError(AgentError):
    """Агент не найден."""
    pass


class AgentProcessingError(AgentError):
    """Ошибка обработки запроса агентом."""
    pass


class IntegrationError(Exception):
    """Ошибка интеграции с внешним API."""
    pass
```

### Обработка

```python
async def process(self, user_input: str) -> dict:
    """Обрабатывает запрос с обработкой ошибок."""
    try:
        result = await self._process(user_input)
        return result
    except AgentNotFoundError:
        logger.error("Agent not found")
        return {
            "error": "Агент не найден",
            "fallback": "coordinator"
        }
    except IntegrationError as e:
        logger.error(f"Integration failed: {e}")
        return {
            "error": "Сервис временно недоступен",
            "retry": True
        }
    except Exception as e:
        logger.exception("Unexpected error")
        return {
            "error": "Произошла ошибка. Попробуйте позже."
        }
```

---

## 🎨 Best Practices

### 1. Код

- ✅ Используйте type hints везде
- ✅ Пишите docstrings для публичных методов
- ✅ Следуйте PEP 8
- ✅ Используйте async/await для I/O операций
- ❌ Не используйте `import *`
- ❌ Не игнорируйте исключения молча
- ❌ Не делайте слишком большие функции (>50 строк)

### 2. База данных

- ✅ Используйте индексы для часто запрашиваемых полей
- ✅ Используйте транзакции для связанных операций
- ✅ Валидируйте данные перед сохранением
- ❌ Не делайте N+1 запросов
- ❌ Не храните чувствительные данные в открытом виде

### 3. API

- ✅ Используйте retry с exponential backoff
- ✅ Устанавливайте таймауты
- ✅ Кэшируйте частые запросы
- ✅ Логируйте все внешние запросы
- ❌ Не храните API ключи в коде
- ❌ Не игнорируйте rate limits

### 4. Безопасность

- ✅ Валидируйте все входные данные
- ✅ Используйте параметризованные запросы
- ✅ Шифруйте чувствительные данные
- ✅ Логируйте попытки доступа
- ❌ Не логируйте пароли и токены
- ❌ Не доверяйте пользовательскому вводу

---

## 📝 Чеклист перед коммитом

```markdown
- [ ] Код отформатирован (black, isort)
- [ ] Линтинг пройден (flake8, mypy)
- [ ] Все тесты проходят
- [ ] Добавлены тесты для нового кода
- [ ] Обновлена документация
- [ ] Обновлён PROGRESS.md
- [ ] Обновлён PROJECT_STATE.json
- [ ] Коммит сообщение соответствует формату
- [ ] Нет секретов в коде
- [ ] Проверена безопасность (bandit)
```

---

## 🆘 Что делать если...

### ...не знаете как реализовать функцию?

1. Проверьте PROJECT_PROMPT.md - там может быть описание
2. Посмотрите на похожие реализации в коде
3. Проверьте документацию используемых библиотек
4. Спросите у пользователя, предложив варианты

### ...тесты не проходят?

1. Прочитайте сообщение об ошибке внимательно
2. Запустите конкретный тест с -vv для деталей
3. Проверьте фикстуры и моки
4. Добавьте print/logging для отладки
5. Упростите тест до минимума

### ...возникла ошибка в production?

1. Проверьте логи в Sentry
2. Воспроизведите локально
3. Добавьте тест, который ловит баг
4. Исправьте
5. Задеплойте hotfix

### ...нужно добавить новую зависимость?

1. Проверьте что она действительно нужна
2. Выберите популярную и поддерживаемую библиотеку
3. Добавьте через Poetry: `poetry add package`
4. Обновите requirements.txt: `poetry export -f requirements.txt`
5. Задокументируйте зачем она нужна

---

## 🎓 Полезные ресурсы

### Документация

- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiogram](https://docs.aiogram.dev/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)

### Инструменты

- [Poetry](https://python-poetry.org/docs/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [pytest](https://docs.pytest.org/)
- [black](https://black.readthedocs.io/)

### Паттерны

- [Python Design Patterns](https://refactoring.guru/design-patterns/python)
- [Async Patterns](https://www.roguelynn.com/words/asyncio-we-did-it-wrong/)

---

**Версия:** 1.0.0  
**Последнее обновление:** 2026-05-23
