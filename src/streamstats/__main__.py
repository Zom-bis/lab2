
import argparse
import logging
import sys
from pathlib import Path

from streamstats.analysis import analyze_files
from streamstats.errors import ConfigError, StreamStatsError
from streamstats.report import build_report, report_to_json, write_report

EXIT_OK = 0
EXIT_ERROR = 2


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="streamstats", description="Статистика по событиям из файлов CSV и JSONL."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="проанализировать файлы и построить отчёт")
    analyze.add_argument("inputs", nargs="+", help="входные файлы")
    analyze.add_argument("--format", required=True, help="формат файлов: csv или jsonl")
    analyze.add_argument("--output", help="куда записать JSON-отчёт (по умолчанию — на экран)")
    analyze.add_argument(
        "--skip-invalid",
        action="store_true",
        help="пропускать ошибочные строки вместо остановки",
    )
    analyze.add_argument(
        "--top", type=int, default=5, help="сколько источников ошибок выводить (по умолчанию 5)"
    )
    return parser


def run_analyze(args: argparse.Namespace) -> None:
    inputs = [Path(name) for name in args.inputs]
    for path in inputs:
        if not path.is_file():
            raise ConfigError(f"входной файл не найден: {path}")
    if args.top < 1:
        raise ConfigError("--top должен быть положительным числом")

    output = Path(args.output) if args.output else None
    if output is not None and any(output.resolve() == path.resolve() for path in inputs):
        raise ConfigError("отчёт нельзя записывать поверх входного файла")

    stats = analyze_files(inputs, args.format, skip_invalid=args.skip_invalid)
    report = build_report(stats, top_n=args.top)

    if output is None:
        print(report_to_json(report))
    else:
        write_report(report, output)


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)  # при неверных аргументах argparse сам выходит с кодом 2
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        run_analyze(args)
    except StreamStatsError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
