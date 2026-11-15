# Авансы по договорам

Небольшое HTTP-приложение для отчёта по работам и платежам подрядчикам на выбранную дату. FastAPI загружает CSV в SQLite и выполняет расчёт; React показывает итоги по договорам и каждой работе.

## Быстрый запуск

Требуются **Python 3.13+** и **Node.js 22.12+**. Команды запуска выполняются из корня проекта в PowerShell.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Открыть: <http://127.0.0.1:8000>. Начальная дата интерфейса — **10.11.2026**.

SQLite создаётся как `backend/report.db` при запуске и заново заполняется из `data/*.csv`. После изменения CSV перезапустите backend. База и production-сборка не хранятся в Git.

## Режим разработки

Запустите backend с автоперезагрузкой:

```powershell
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

Во втором терминале запустите Vite:

```powershell
npm --prefix frontend run dev
```

Откройте <http://127.0.0.1:5173>. Запросы `/api` автоматически проксируются на порт `8000`.

## API

- `GET /api/report?report_date=2026-11-10` — отчёт на дату.
- `GET /api/health` — проверка доступности.
- `GET /docs` — интерактивная OpenAPI-документация.

Денежные значения передаются в JSON строками с двумя знаками после запятой, например `"315000.00"`. Это исключает потерю точности на границе API.

Контрольный результат на **10.11.2026**:

| Договор | Сумма договора | Активные работы | Оплачено | Осталось | Не распределено |
|---|---:|---:|---:|---:|---:|
| D-1 | 600 000,00 ₽ | 500 000,00 ₽ | 315 000,00 ₽ | 185 000,00 ₽ | 0,00 ₽ |
| D-2 | 90 000,00 ₽ | 90 000,00 ₽ | 75 000,00 ₽ | 15 000,00 ₽ | 0,00 ₽ |

Правила и их последствия описаны в [DECISIONS.md](DECISIONS.md). Краткая инструкция — в [ACCOUNTANT.md](ACCOUNTANT.md).

## Проверки

Backend (команды выполняются из папки `backend`):

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python -m ruff check .
..\.venv\Scripts\python -m ruff format --check .
Set-Location ..
```

Frontend:

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Тесты охватывают эталонный расчёт, даты оплаты и возврата, очередь и будущие платежи, переплату, статусы работ, копейки и большие суммы, ошибки CSV, API, отображение, смену даты и состояния ошибок.

## Структура

```text
backend/app/       FastAPI, SQLite и расчёт
backend/tests/     тесты расчёта и API
frontend/src/      React-компоненты, стили и тесты
data/              исходные CSV и описание их формата
DECISIONS.md       принятые решения и альтернативы
ACCOUNTANT.md      записка бухгалтеру
```
