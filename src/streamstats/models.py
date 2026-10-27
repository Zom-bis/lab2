
from dataclasses import dataclass
from datetime import UTC, datetime

from streamstats.errors import InvalidEventError, InvalidTimestampError

# Допустимые уровни. Чтобы добавить новый уровень (например, NOTICE),
# достаточно дописать его сюда.
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

# Уровни, которые считаются ошибками для top-N источников.
ERROR_LEVELS = ("ERROR", "CRITICAL")

REQUIRED_FIELDS = ("timestamp", "level", "source", "message")


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    level: str
    source: str
    message: str


def parse_timestamp(value: str, line: int | None = None) -> datetime:
    """Разбирает дату ISO 8601. Дату без часового пояса считаем UTC."""
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise InvalidTimestampError(
            f"неверная дата {value!r}, нужен формат ISO 8601", line=line, field="timestamp"
        ) from None
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result


def event_from_dict(data: dict[str, object], line: int | None = None) -> Event:
    """Проверяет словарь с полями и создаёт Event."""
    for name in REQUIRED_FIELDS:
        if name not in data or data[name] is None:
            raise InvalidEventError("отсутствует обязательное поле", line=line, field=name)
        if not isinstance(data[name], str):
            raise InvalidEventError("значение должно быть строкой", line=line, field=name)

    timestamp = parse_timestamp(str(data["timestamp"]), line)

    level = str(data["level"])
    if level not in LEVELS:
        raise InvalidEventError(
            f"неизвестный уровень {level!r}, допустимы: {', '.join(LEVELS)}",
            line=line,
            field="level",
        )

    source = str(data["source"])
    if source.strip() == "":
        raise InvalidEventError("источник не может быть пустым", line=line, field="source")

    return Event(timestamp=timestamp, level=level, source=source, message=str(data["message"]))
