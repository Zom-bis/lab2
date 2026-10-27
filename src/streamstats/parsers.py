
import csv
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from streamstats.errors import InvalidEventError, UnsupportedFormatError
from streamstats.models import REQUIRED_FIELDS, Event, event_from_dict

# utf-8-sig понимает и обычный UTF-8, и UTF-8 с BOM (так сохраняет Excel).
ENCODING = "utf-8-sig"


@dataclass(frozen=True)
class ParsedLine:
    """Результат разбора одной строки: либо событие, либо ошибка."""

    line: int
    event: Event | None = None
    error: InvalidEventError | None = None


Parser = Callable[[Path], Iterator[ParsedLine]]


def _make_parsed_line(data: dict[str, object], line: int) -> ParsedLine:
    try:
        return ParsedLine(line=line, event=event_from_dict(data, line))
    except InvalidEventError as error:
        return ParsedLine(line=line, error=error)


def parse_jsonl(path: Path) -> Iterator[ParsedLine]:
    """Читает JSONL: одна строка файла — один JSON-объект."""
    with open(path, encoding=ENCODING) as file:
        for line_no, text in enumerate(file, start=1):  # построчное чтение
            if text.strip() == "":
                continue  # пустые строки (например, в конце файла) не считаем ошибкой
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                yield ParsedLine(line_no, error=InvalidEventError(f"неверный JSON: {exc.msg}", line_no))
                continue
            if not isinstance(data, dict):
                yield ParsedLine(line_no, error=InvalidEventError("ожидался JSON-объект", line_no))
                continue
            yield _make_parsed_line(data, line_no)


def parse_csv(path: Path) -> Iterator[ParsedLine]:
    """Читает CSV, первая строка — заголовок с именами столбцов."""
    with open(path, encoding=ENCODING, newline="") as file:
        reader = csv.reader(file)  # csv.reader тоже читает файл построчно
        header = next(reader, None)
        if header is None:
            return  # пустой файл — событий нет
        header = [name.strip() for name in header]
        missing = [name for name in REQUIRED_FIELDS if name not in header]
        if missing:
            # Без нужных столбцов ни одну строку разобрать нельзя — это ошибка всего файла.
            raise InvalidEventError(f"в заголовке CSV нет столбцов: {', '.join(missing)}", line=1)

        for row in reader:
            line_no = reader.line_num
            if not row:
                continue  # пустая строка
            if len(row) != len(header):
                error = InvalidEventError(
                    f"ожидалось столбцов: {len(header)}, получено: {len(row)}", line_no
                )
                yield ParsedLine(line_no, error=error)
                continue
            yield _make_parsed_line(dict(zip(header, row, strict=True)), line_no)


PARSERS: dict[str, Parser] = {
    "csv": parse_csv,
    "jsonl": parse_jsonl,
}


def get_parser(fmt: str) -> Parser:
    parser = PARSERS.get(fmt.lower())
    if parser is None:
        raise UnsupportedFormatError(
            f"формат {fmt!r} не поддерживается, допустимы: {', '.join(PARSERS)}"
        )
    return parser
