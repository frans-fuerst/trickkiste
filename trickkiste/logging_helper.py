#!/usr/bin/env python3

"""Common stuff shared among modules"""

import logging
import os
import sys
import traceback
from collections.abc import Iterable

from rich.console import Console
from rich.logging import RichHandler
from rich.markup import escape as markup_escape

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


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


def setup_logging(logger: logging.Logger, level: str | int = "INFO") -> None:
    """Make logging fun"""

    class CustomLogger(logging.getLoggerClass()):  # type: ignore[misc]
        """Injects the 'stack' element"""

        def makeRecord(self, *args: object, **kwargs: object) -> logging.LogRecord:
            """Adds 'stack' element to given record"""
            kwargs.setdefault("extra", {})["stack"] = stack_str(5)  # type: ignore[index]
            return super().makeRecord(*args, **kwargs)  # type: ignore[no-any-return]

    logging.setLoggerClass(CustomLogger)

    used_level = getattr(logging, level.split("_")[-1]) if isinstance(level, str) else level

    if not logging.getLogger().hasHandlers():
        logging.getLogger().setLevel(logging.WARNING)
        shandler = RichHandler(
            show_time=False,
            show_path=False,
            markup=True,
            console=Console(
                stderr=True, color_system="standard" if os.environ.get("FORCE_COLOR") else "auto"
            ),
        )
        logging.getLogger().addHandler(shandler)
        shandler.setLevel(used_level)
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
    logger.setLevel(used_level)
