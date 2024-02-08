#!/usr/bin/env python3

"""Common stuff shared among modules"""

import logging
import os
import sys
import traceback
from argparse import ArgumentParser
from collections.abc import Iterable

from rich.console import Console
from rich.logging import RichHandler
from rich.markup import escape as markup_escape

LOG_LEVELS = ("ALL_DEBUG", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")


def apply_common_logging_cli_args(parser: ArgumentParser) -> None:
    """Decorates given @parser with arguments for logging"""
    parser.add_argument(
        "--log-level",
        "-l",
        choices=LOG_LEVELS,
        help="Sets the logging level - ALL_DEBUG sets all other loggers to DEBUG, too",
        type=str.upper,
        default="INFO",
    )


def stack_str(depth: int = 0) -> str:
    """Returns a short local function call stack"""

    def stack_fns() -> Iterable[str]:
        stack = list(
            reversed(
                traceback.extract_stack(sys._getframe(depth))  # pylint: disable=protected-access
            )
        )

        for site in stack:
            if site.filename != stack[0].filename or site.name == "<module>":
                break
            yield site.name

    return ">".join(reversed(list(stack_fns())))


def setup_logging(logger: logging.Logger | str, level: str | int = "INFO") -> None:
    """Make logging fun"""

    class CustomLogger(  # pylint: disable=unused-variable
        logging.getLoggerClass()  # type: ignore[misc]
    ):
        """Injects the 'stack' element"""

        def makeRecord(self, *args: object, **kwargs: object) -> logging.LogRecord:
            """Adds 'stack' element to given record"""
            kwargs.setdefault("extra", {})["stack"] = stack_str(5)  # type: ignore[index]
            return super().makeRecord(*args, **kwargs)  # type: ignore[no-any-return]

    # currently this introduces more problems then benefits
    # logging.setLoggerClass(CustomLogger)

    # log level for everything
    root_log_level = logging.DEBUG if level == "ALL_DEBUG" else logging.WARNING

    # log level for provided @logger
    used_level = getattr(logging, level.split("_")[-1]) if isinstance(level, str) else level

    if not logging.getLogger().hasHandlers():
        logging.getLogger().setLevel(root_log_level)
        shandler = RichHandler(
            show_time=False,
            show_path=False,
            markup=True,
            console=Console(
                stderr=True, color_system="standard" if os.environ.get("FORCE_COLOR") else "auto"
            ),
        )
        logging.getLogger().addHandler(shandler)
        shandler.setLevel(min(used_level, root_log_level))
        shandler.setFormatter(logging.Formatter("│ [grey]%(name)-15s[/] │ [bold]%(message)s[/]"))

        # logging.basicConfig(
        #   format="%(name)s %(levelname)s: %(message)s",
        #   datefmt="%Y-%m-%d %H:%M:%S",
        #   level=logging.DEBUG if level == "ALL_DEBUG" else logging.WARNING,
        # )

        def markup_escaper(record: logging.LogRecord) -> bool:
            record.args = record.args and tuple(
                markup_escape(arg) if isinstance(arg, str) else arg for arg in record.args
            )
            record.msg = markup_escape(record.msg)
            return True

        shandler.addFilter(markup_escaper)

    # for lev in LOG_LEVELS:
    #    logging.addLevelName(getattr(logging, lev), f"{lev[0] * 2}")

    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    (logging.getLogger(logger) if isinstance(logger, str) else logger).setLevel(used_level)
