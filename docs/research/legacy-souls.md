# Legacy SOUL files (not wired to production bots)

Эти файлы в `src/agents_tg/agents/souls/` **не** подключены в `specialists.py` / `personal_assistant.py` / LangGraph nodes. Не удалять без явного согласия — только архивный список.

| Файл | Примечание |
|------|------------|
| `planner_soul.md` | Старый планировщик |
| `integrator_soul.md` | Интегратор |
| `tutor_soul.md` | Тьютор |
| `finance_soul.md` | Финансы (дублирует имя Ульяны в черновиках) |
| `assistant_soul.md` | Заменён `personal_assistant.md` |
| `coordinator_soul.md` | Координатор |
| `sports_analyst.md` | Содержимое перенесено в `research.md`; alias в `identity.py` |

Прод-агенты: orchestrator, personal_assistant, research, coder, security_ai, business_manager, marketing, general.
