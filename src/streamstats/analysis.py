
import logging
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from streamstats.errors import ConfigError, InvalidEventError
from streamstats.models import ERROR_LEVELS, Event
from streamstats.parsers import get_parser

logger = logging.getLogger(__name__)


class Stats:
    """Накопленная статистика по одному или нескольким файлам."""

    def __init__(self) -> None:
        self.total = 0
        self.skipped = 0
        self.by_level: Counter[str] = Counter()
        self.by_source: Counter[str] = Counter()
        self.error_sources: Counter[str] = Counter()
        self.first: datetime | None = None
        self.last: datetime | None = None

    def add(self, event: Event) -> None:
        self.total += 1
        self.by_level[event.level] += 1
        self.by_source[event.source] += 1
        if event.level in ERROR_LEVELS:
            self.error_sources[event.source] += 1
        if self.first is None or event.timestamp < self.first:
            self.first = event.timestamp
        if self.last is None or event.timestamp > self.last:
            self.last = event.timestamp

    def top_error_sources(self, n: int = 5) -> list[tuple[str, int]]:
        """Top-N источников ошибок.

        Сортировка: по количеству (по убыванию), при равенстве — по имени
        (по алфавиту). Так результат всегда одинаковый.
        """
        items = sorted(self.error_sources.items(), key=lambda item: (-item[1], item[0]))
        return items[:n]


def analyze_files(paths: Iterable[Path], fmt: str, skip_invalid: bool = False) -> Stats:
    """Обрабатывает файлы по очереди и складывает статистику в один Stats."""
    parser = get_parser(fmt)
    stats = Stats()
    for file_no, path in enumerate(paths, start=1):
        label = f"#{file_no} ({path})"
        try:
            for item in parser(path):
                if item.error is not None:
                    item.error.file = label
                    if not skip_invalid:
                        raise item.error
                    logger.warning("пропущена строка: %s", item.error)
                    stats.skipped += 1
                elif item.event is not None:
                    stats.add(item.event)
        except InvalidEventError as error:
            if error.file is None:
                error.file = label
            raise
        except UnicodeDecodeError as exc:
            raise InvalidEventError(f"файл {label} не в кодировке UTF-8") from exc
        except OSError as exc:
            raise ConfigError(f"не удалось прочитать файл {path}: {exc.strerror}") from exc
    return stats
