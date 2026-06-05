# E2E prod sign-off (solo owner)

Шаблон для [`implementation-notes.md`](implementation-notes.md). Часовой пояс: Europe/Moscow.

**Автоматизация VPS:** `python scripts/vps_configure_prod.py` → [`last_vps_e2e_automated.txt`](last_vps_e2e_automated.txt).

## Automated (VPS script, 2026-06-04)

| ID | Pass | Дата | Примечание |
|----|------|------|------------|
| W1 #5 curl :8080 health + DB | Pass | 2026-06-04 | `scripts/vps_configure_prod.py` |
| W4 #17 API без токена → 401 | Pass | 2026-06-04 | automated |
| W4 #17 API с Bearer → 200 | Pass | 2026-06-04 | automated |
| REQUIRE_CONFIRM=true на VPS | Pass | 2026-06-04 | `.env`, DEBUG=false |
| systemctl agents-tg active | Pass | 2026-06-04 | automated |

## W1–W6 (Telegram — manual)

См. [`E2E_TELEGRAM_CHECKLIST.md`](E2E_TELEGRAM_CHECKLIST.md).

| # | Pass | Дата | Примечание |
|---|------|------|------------|
| 1 | | | Привет Егор — **manual** |
| 2 | | | Длинный ответ Руслан — **manual** |
| 3 | | | Напоминание 3 мин Эльза — **manual** |
| 5 | Pass | 2026-06-04 | curl :8080 — см. automated выше |
| 6 | | | Ульяна deep_research — **manual** |
| 7 | | | Егор план 2+ шагов — **manual** |

## W11 delegation (D1–D6) — manual

| ID | Pass | Дата | Примечание |
|----|------|------|------------|
| D1 DM multi-step | | | **manual** |
| D2 Group multi-step | | | **manual** |
| D5 cancel plan | | | **manual** |
| D6 REQUIRE_CONFIRM + replay | | | **manual** (Эльза, Да/Нет) |

## MVP integration smoke (фаза 2) — manual

| Integration | Pass | Дата | Примечание |
|-------------|------|------|------------|
| Calendar tool | | | **manual** |
| GitHub list issues | | | **manual** |
| Research cite format | | | **manual** |
