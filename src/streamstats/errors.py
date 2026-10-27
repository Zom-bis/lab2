
class StreamStatsError(Exception):
    """Базовая ошибка пакета. CLI ловит только её и её наследников."""


class UnsupportedFormatError(StreamStatsError):
    """Формат входного файла не поддерживается."""


class ConfigError(StreamStatsError):
    """Неверные параметры командной строки (нет файла, плохой путь и т.п.)."""


class InvalidEventError(StreamStatsError):
    """Строка файла не является корректным событием.

    Хранит номер строки и имя поля, чтобы сообщение было понятным.
    Имя файла дописывается позже, в analysis.py, когда оно известно.
    """

    def __init__(self, reason: str, line: int | None = None, field: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.line = line
        self.field = field
        self.file: str | None = None

    def __str__(self) -> str:
        where = []
        if self.file is not None:
            where.append(f"файл {self.file}")
        if self.line is not None:
            where.append(f"строка {self.line}")
        if self.field is not None:
            where.append(f"поле '{self.field}'")
        if not where:
            return self.reason
        return ", ".join(where) + ": " + self.reason


class InvalidTimestampError(InvalidEventError):
    """Поле timestamp не в формате ISO 8601."""
