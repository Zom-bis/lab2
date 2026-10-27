
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from streamstats.analysis import Stats
from streamstats.errors import ConfigError
from streamstats.models import LEVELS


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def build_report(stats: Stats, top_n: int = 5) -> dict[str, Any]:
    return {
        "total_events": stats.total,
        "skipped_lines": stats.skipped,
        "levels": {level: stats.by_level.get(level, 0) for level in LEVELS},
        "sources": dict(sorted(stats.by_source.items())),
        "top_error_sources": [
            {"source": source, "count": count} for source, count in stats.top_error_sources(top_n)
        ],
        "first_timestamp": _iso(stats.first),
        "last_timestamp": _iso(stats.last),
    }


def report_to_json(report: dict[str, Any]) -> str:
    # ensure_ascii=False — чтобы кириллица осталась кириллицей, а не О...
    return json.dumps(report, ensure_ascii=False, indent=2)


def write_report(report: dict[str, Any], path: Path) -> None:
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(report_to_json(report) + "\n")
    except OSError as exc:
        raise ConfigError(f"не удалось записать отчёт в {path}: {exc.strerror}") from exc
