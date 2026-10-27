
import json
from pathlib import Path

import pytest

# Одни и те же события — для CSV и для JSONL.
EVENTS = [
    {"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": "auth", "message": "Вход выполнен"},
    {"timestamp": "2026-01-01T10:05:00", "level": "ERROR", "source": "db", "message": "Ошибка соединения"},
    {"timestamp": "2026-01-01T09:00:00", "level": "CRITICAL", "source": "db", "message": "База упала"},
    {"timestamp": "2026-01-01T11:00:00", "level": "ERROR", "source": "api", "message": "timeout"},
    {"timestamp": "2026-01-01T10:30:00", "level": "DEBUG", "source": "auth", "message": "токен, \"ok\""},
]


def write_jsonl(path: Path, records: list[dict[str, str]]) -> Path:
    with open(path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_csv(path: Path, records: list[dict[str, str]]) -> Path:
    import csv

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "level", "source", "message"])
        writer.writeheader()
        writer.writerows(records)
    return path


@pytest.fixture
def jsonl_file(tmp_path: Path) -> Path:
    return write_jsonl(tmp_path / "events.jsonl", EVENTS)


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    return write_csv(tmp_path / "events.csv", EVENTS)
