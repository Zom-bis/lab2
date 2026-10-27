
import json
import os
import subprocess
import sys
from pathlib import Path

from streamstats.__main__ import main

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "streamstats", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def test_cli_writes_report(tmp_path: Path, csv_file: Path) -> None:
    output = tmp_path / "report.json"
    result = run_cli("analyze", str(csv_file), "--format", "csv", "--output", str(output))
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["total_events"] == 5
    assert report["top_error_sources"][0] == {"source": "db", "count": 2}


def test_cli_stops_on_bad_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{oops\n", encoding="utf-8")
    output = tmp_path / "report.json"
    result = run_cli("analyze", str(path), "--format", "jsonl", "--output", str(output))
    assert result.returncode == 2
    assert "строка 1" in result.stderr
    assert not output.exists()


def test_cli_skip_invalid(tmp_path: Path, jsonl_file: Path) -> None:
    with open(jsonl_file, "a", encoding="utf-8") as file:
        file.write("{oops\n")
    result = run_cli("analyze", str(jsonl_file), "--format", "jsonl", "--skip-invalid")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["total_events"] == 5
    assert report["skipped_lines"] == 1
    assert "WARNING" in result.stderr


def test_cli_help() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "analyze" in result.stdout


def test_cli_unsupported_format(jsonl_file: Path) -> None:
    assert main(["analyze", str(jsonl_file), "--format", "xml"]) == 2


def test_cli_missing_file(tmp_path: Path) -> None:
    assert main(["analyze", str(tmp_path / "nope.csv"), "--format", "csv"]) == 2


def test_cli_does_not_overwrite_input(jsonl_file: Path) -> None:
    before = jsonl_file.read_bytes()
    assert main(["analyze", str(jsonl_file), "--format", "jsonl", "--output", str(jsonl_file)]) == 2
    assert jsonl_file.read_bytes() == before


def test_cli_top_n(tmp_path: Path, jsonl_file: Path) -> None:
    output = tmp_path / "report.json"
    assert main(["analyze", str(jsonl_file), "--format", "jsonl", "--top", "1", "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["top_error_sources"] == [{"source": "db", "count": 2}]
