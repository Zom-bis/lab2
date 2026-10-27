# Лабораторная работа 2. Потоковый анализатор файлов

Пакет `streamstats` читает события из CSV и JSONL построчно и строит JSON-отчёт:
общее число событий, число по уровням и источникам, top-5 источников ошибок
(ERROR/CRITICAL), первая и последняя временная метка, число пропущенных строк.

## Установка

```
pip install -e .[dev]
```

Без установки можно запускать из папки `lab_02`, указав путь к коду:
`set PYTHONPATH=src` (cmd) или `$env:PYTHONPATH="src"` (PowerShell).

## Запуск

```
python -m streamstats analyze a.csv b.csv --format csv --output report.json
python -m streamstats analyze logs.jsonl --format jsonl --skip-invalid
python -m streamstats --help
```

Параметры:

- `--format csv|jsonl` — формат всех входных файлов;
- `--output FILE` — куда записать отчёт; если не указан, отчёт печатается на экран;
- `--skip-invalid` — пропускать ошибочные строки (в лог пишется WARNING, в отчёте растёт `skipped_lines`);
- `--top N` — сколько источников ошибок выводить (по умолчанию 5).

Без `--skip-invalid` первая ошибочная строка останавливает обработку: в stderr выводится
номер файла, номер строки и поле, код выхода — 2.

## Формат входных данных

Обязательные поля: `timestamp` (ISO 8601), `level` (DEBUG, INFO, WARNING, ERROR, CRITICAL),
`source` (непустая строка), `message` (строка). Файлы читаются в UTF-8.

CSV — первая строка заголовок:

```
timestamp,level,source,message
2026-01-01T10:00:00,ERROR,db,Ошибка соединения
```

JSONL — один JSON-объект на строку:

```
{"timestamp": "2026-01-01T10:00:00", "level": "ERROR", "source": "db", "message": "Ошибка соединения"}
```

Дата без часового пояса считается UTC.

## Пример отчёта

```json
{
  "total_events": 5,
  "skipped_lines": 0,
  "levels": {"DEBUG": 1, "INFO": 1, "WARNING": 0, "ERROR": 2, "CRITICAL": 1},
  "sources": {"api": 1, "auth": 2, "db": 2},
  "top_error_sources": [{"source": "db", "count": 2}, {"source": "api", "count": 1}],
  "first_timestamp": "2026-01-01T09:00:00+00:00",
  "last_timestamp": "2026-01-01T11:00:00+00:00"
}
```

## Структура

| Файл | Что делает |
|---|---|
| `errors.py` | исключения: `StreamStatsError` и наследники `UnsupportedFormatError`, `InvalidEventError`, `InvalidTimestampError`, `ConfigError` |
| `models.py` | класс `Event`, список уровней, проверка полей |
| `parsers.py` | генераторы `parse_csv` и `parse_jsonl`, выбор парсера по формату |
| `analysis.py` | класс `Stats` (счётчики) и `analyze_files` (обработка файлов, два режима ошибок) |
| `report.py` | сборка отчёта и запись в JSON |
| `__main__.py` | командная строка; ловит `StreamStatsError`, печатает в stderr, код 2 |

## Потоковость и память

Построчную обработку гарантируют циклы `for text in file` в `parse_jsonl` и
`for row in reader` в `parse_csv` (`parsers.py`). Оба парсера — генераторы (`yield`),
поэтому в каждый момент в памяти находится одна строка файла.
`read()` и `readlines()` не используются.

`Stats.add` не сохраняет события, а только увеличивает счётчики. Дополнительная память:
O(число разных уровней + число разных источников) плюс одна текущая строка.
От количества строк в файле она не зависит.

## Ответы для защиты

- **Уровень NOTICE.** Валидация уровня находится в одном месте — кортеж `LEVELS` в
  `models.py`. Достаточно добавить туда `"NOTICE"`: проверка и раздел `levels` в отчёте
  подхватят его сами.
- **top-5 → top-N.** Уже сделано параметром: `Stats.top_error_sources(n)`,
  `build_report(stats, top_n)` и флаг `--top N`. Логика сортировки одна.
- **Детерминированный top.** Сортировка по ключу `(-количество, имя)`: при равном
  количестве источники идут по алфавиту.
- **Исходные файлы не изменяются.** Входные файлы открываются только на чтение; если
  `--output` указывает на входной файл, программа выдаёт ошибку.

## Проверка

```
python -m pytest
ruff check .
python -m streamstats --help
```
