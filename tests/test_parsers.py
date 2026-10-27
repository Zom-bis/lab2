import inspect
from pathlib import Path

import pytest

from conftest import EVENTS
from streamstats.errors import InvalidEventError, InvalidTimestampError, UnsupportedFormatError
from streamstats.parsers import get_parser, parse_csv, parse_jsonl


def test_jsonl_parser_reads_all_events(jsonl_file: Path) -> None:
    items = list(parse_jsonl(jsonl_file))
    assert len(items) == len(EVENTS)
    assert all(item.error is None for item in items)
    assert items[0].event is not None
    assert items[0].event.message == "Вход выполнен"
    assert [item.line for item in items] == [1, 2, 3, 4, 5]


def test_csv_parser_reads_all_events(csv_file: Path) -> None:
    items = list(parse_csv(csv_file))
    assert len(items) == len(EVENTS)
    assert all(item.error is None for item in items)
    # Запятая и кавычки внутри сообщения не ломают разбор CSV.
    assert items[4].event is not None
    assert items[4].event.message == 'токен, "ok"'
    # Строка 1 — заголовок, данные начинаются со строки 2.
    assert items[0].line == 2


def test_parsers_are_generators(jsonl_file: Path, csv_file: Path) -> None:
    assert inspect.isgenerator(parse_jsonl(jsonl_file))
    assert inspect.isgenerator(parse_csv(csv_file))


def test_empty_files_give_no_events(tmp_path: Path) -> None:
    (tmp_path / "empty.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "empty.csv").write_text("", encoding="utf-8")
    assert list(parse_jsonl(tmp_path / "empty.jsonl")) == []
    assert list(parse_csv(tmp_path / "empty.csv")) == []


def test_broken_json_reports_line_7(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    lines = [
        '{"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": "a", "message": "x"}'
    ] * 6
    lines.append("{это не json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    items = list(parse_jsonl(path))
    assert len(items) == 7
    error = items[6].error
    assert error is not None
    assert error.line == 7
    assert "строка 7" in str(error)


def test_bad_timestamp_reports_field_and_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "timestamp,level,source,message\n"
        "2026-01-01T10:00:00,INFO,a,ok\n"
        "вчера,INFO,a,bad\n",
        encoding="utf-8",
    )
    items = list(parse_csv(path))
    error = items[1].error
    assert isinstance(error, InvalidTimestampError)
    assert error.line == 3
    assert error.field == "timestamp"
    assert "поле 'timestamp'" in str(error)


@pytest.mark.parametrize(
    ("record", "field"),
    [
        ({"timestamp": "2026-01-01T10:00:00", "level": "LOUD", "source": "a", "message": "x"}, "level"),
        ({"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": "  ", "message": "x"}, "source"),
        ({"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": "a"}, "message"),
        ({"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": 5, "message": "x"}, "source"),
    ],
)
def test_invalid_fields(tmp_path: Path, record: dict[str, object], field: str) -> None:
    import json

    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    items = list(parse_jsonl(path))
    assert items[0].error is not None
    assert items[0].error.field == field


def test_jsonl_line_must_be_object(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("[1, 2, 3]\n", encoding="utf-8")
    items = list(parse_jsonl(path))
    assert items[0].error is not None


def test_csv_wrong_column_count(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("timestamp,level,source,message\n2026-01-01T10:00:00,INFO\n", encoding="utf-8")
    items = list(parse_csv(path))
    assert items[0].error is not None
    assert items[0].error.line == 2


def test_csv_header_without_required_column(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("timestamp,level,message\n2026-01-01T10:00:00,INFO,x\n", encoding="utf-8")
    with pytest.raises(InvalidEventError, match="source"):
        list(parse_csv(path))


def test_get_parser() -> None:
    assert get_parser("csv") is parse_csv
    assert get_parser("JSONL") is parse_jsonl
    with pytest.raises(UnsupportedFormatError):
        get_parser("xml")
