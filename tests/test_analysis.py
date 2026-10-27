import logging
from pathlib import Path

import pytest

from conftest import EVENTS, write_jsonl
from streamstats.analysis import Stats, analyze_files
from streamstats.errors import InvalidEventError
from streamstats.report import build_report, report_to_json


def test_empty_file_gives_zero_report(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    report = build_report(analyze_files([path], "jsonl"))
    assert report["total_events"] == 0
    assert report["skipped_lines"] == 0
    assert report["levels"] == {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    assert report["sources"] == {}
    assert report["top_error_sources"] == []
    assert report["first_timestamp"] is None
    assert report["last_timestamp"] is None


def test_statistics_values(jsonl_file: Path) -> None:
    report = build_report(analyze_files([jsonl_file], "jsonl"))
    assert report["total_events"] == 5
    assert report["levels"]["ERROR"] == 2
    assert report["levels"]["WARNING"] == 0
    assert report["sources"] == {"api": 1, "auth": 2, "db": 2}
    assert report["top_error_sources"] == [{"source": "db", "count": 2}, {"source": "api", "count": 1}]
    assert report["first_timestamp"] == "2026-01-01T09:00:00+00:00"
    assert report["last_timestamp"] == "2026-01-01T11:00:00+00:00"


def test_csv_and_jsonl_give_same_statistics(csv_file: Path, jsonl_file: Path) -> None:
    from_csv = build_report(analyze_files([csv_file], "csv"))
    from_jsonl = build_report(analyze_files([jsonl_file], "jsonl"))
    assert from_csv == from_jsonl


def test_several_files_are_merged(tmp_path: Path) -> None:
    first = write_jsonl(tmp_path / "a.jsonl", EVENTS[:2])
    second = write_jsonl(tmp_path / "b.jsonl", EVENTS[2:])
    third = write_jsonl(tmp_path / "c.jsonl", EVENTS)
    report = build_report(analyze_files([first, second, third], "jsonl"))
    assert report["total_events"] == len(EVENTS) * 2
    assert report["sources"] == {"api": 2, "auth": 4, "db": 4}


def test_strict_mode_stops_with_file_and_line(tmp_path: Path) -> None:
    good = write_jsonl(tmp_path / "good.jsonl", EVENTS)
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"timestamp": "2026-01-01T10:00:00", "level": "INFO", "source": "a", "message": "x"}\n'
                   "сломанная строка\n", encoding="utf-8")
    with pytest.raises(InvalidEventError) as info:
        analyze_files([good, bad], "jsonl")
    message = str(info.value)
    assert "#2" in message
    assert "строка 2" in message


def test_skip_mode_counts_and_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "mixed.csv"
    path.write_text(
        "timestamp,level,source,message\n"
        "2026-01-01T10:00:00,INFO,a,ok\n"
        "не дата,INFO,a,bad\n"
        "2026-01-01T11:00:00,ERROR,b,ok\n",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        stats = analyze_files([path], "csv", skip_invalid=True)
    assert stats.total == 2
    assert stats.skipped == 1
    assert "строка 3" in caplog.text


def test_top_is_deterministic_on_ties() -> None:
    stats = Stats()
    stats.error_sources.update(
        {"zeta": 3, "alpha": 3, "beta": 3, "gamma": 5, "delta": 1, "omega": 3, "eps": 2}
    )
    assert stats.top_error_sources() == [
        ("gamma", 5), ("alpha", 3), ("beta", 3), ("omega", 3), ("zeta", 3),
    ]
    assert stats.top_error_sources(2) == [("gamma", 5), ("alpha", 3)]


def test_cyrillic_is_kept_in_report(tmp_path: Path) -> None:
    path = write_jsonl(tmp_path / "ru.jsonl", [
        {"timestamp": "2026-01-01T10:00:00", "level": "ERROR", "source": "склад", "message": "нет товара"},
    ])
    text = report_to_json(build_report(analyze_files([path], "jsonl")))
    assert "склад" in text
    assert "\\u" not in text


def test_input_file_is_not_changed(jsonl_file: Path) -> None:
    before = jsonl_file.read_bytes()
    analyze_files([jsonl_file], "jsonl")
    assert jsonl_file.read_bytes() == before
