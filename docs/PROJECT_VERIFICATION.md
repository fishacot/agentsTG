---
summary: Команды проверки Python-проекта — pytest, black, flake8, mypy, bandit
read_when: после правок кода, перед коммитом или PR, нужен список verify-команд
---

# PROJECT_VERIFICATION — AI Agents Telegram Assistant

> Команды проверки для проекта. Канон процесса: `AGENTS.md` (CursoRules).

## Команды проверки

| Шаг | Команда | Когда обязательно |
|-----|---------|-------------------|
| **Python тесты** | `pytest tests/ -v --cov=src --cov-report=term-missing` | После любых правок в `src/` |
| **Форматирование** | `black . && isort .` | Перед каждым коммитом |
| **Линтинг** | `flake8 src/ tests/` | Перед каждым коммитом |
| **Type checking** | `mypy src/` | После правок с типами |
| **Безопасность** | `bandit -r src/ -ll` | После правок в auth/security/API |
| **Markdown** | `npm run verify` (если есть package.json) | После правок в `*.md` |
| **Cursor artifacts** | `python scripts/validate_cursor_artifacts.py` | После правок в `.cursor/` |
| **Миграции БД** | `alembic check` | После правок моделей |
| **Зависимости** | `poetry check` | После изменений в pyproject.toml |

## Быстрая проверка (минимум)

```bash
# Форматирование + линтинг + тесты
black . && isort . && flake8 src/ && pytest tests/ -v
```

## Полная проверка (перед PR)

```bash
# 1. Форматирование
black .
isort .

# 2. Линтинг
flake8 src/ tests/
mypy src/

# 3. Безопасность
bandit -r src/ -ll

# 4. Тесты с покрытием
pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# 5. Проверка зависимостей
poetry check

# 6. Проверка миграций (если есть изменения в моделях)
alembic check
```

## Настройка инструментов

### Black (форматирование)
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
```

### isort (сортировка импортов)
```toml
# pyproject.toml
[tool.isort]
profile = "black"
line_length = 88
```

### flake8 (линтинг)
```ini
# .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,.venv,alembic
```

### mypy (type checking)
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### pytest (тестирование)
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers --cov=src"
```

### bandit (безопасность)
```yaml
# .bandit
exclude_dirs:
  - /tests/
  - /venv/
  - /.venv/
```

## Цикл повторов

До **3** попыток исправить падение проверки. Затем:
1. Стоп
2. Запись в `docs/implementation-notes.md` с описанием проблемы
3. Вопрос человеку

## Definition of Done (минимум)

- ✅ Задача выполнена в scope
- ✅ Все применимые команды из таблицы — успех (зелёные)
- ✅ `docs/implementation-notes.md` обновлён с решениями и tradeoffs
- ✅ Нет правок "мимо задачи"
- ✅ Коммит сообщение соответствует формату (conventional commits)

## Pre-commit hooks (опционально)

Для автоматической проверки перед коммитом:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

Установка:
```bash
pip install pre-commit
pre-commit install
```

## CI/CD проверки

GitHub Actions будет запускать те же команды автоматически при push/PR.

См. `.github/workflows/test.yml` (создать при настройке CI).

## Специфичные проверки

### Для агентов
- Проверка промптов на корректность
- Тесты function calling
- Валидация JSON схем

### Для БД
- Проверка миграций: `alembic upgrade head` (в тестовой БД)
- Откат миграций: `alembic downgrade -1`
- Проверка индексов и constraints

### Для интеграций
- Mock тесты для внешних API
- Проверка обработки ошибок API
- Валидация rate limiting

## Troubleshooting

### Тесты падают
```bash
# Запустить конкретный тест с подробным выводом
pytest tests/unit/test_coordinator.py::test_route_to_planner -vv

# С логами
pytest tests/ -v --log-cli-level=DEBUG

# Остановиться на первой ошибке
pytest tests/ -x
```

### Линтер ругается
```bash
# Показать все ошибки с кодами
flake8 src/ --show-source --statistics

# Игнорировать конкретную ошибку (добавить в .flake8)
# noqa: E501  # в конце строки
```

### mypy не проходит
```bash
# Подробный вывод
mypy src/ --show-error-codes --pretty

# Игнорировать конкретную строку
# type: ignore[error-code]
```

---

**Версия:** 1.0.0  
**Последнее обновление:** 2026-05-24
