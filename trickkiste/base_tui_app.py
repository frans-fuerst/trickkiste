#!/usr/bin/env python3

"""A textual base app with common features like a logging window"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments
# pylint: disable=too-many-instance-attributes

import asyncio
import logging
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from rich.logging import RichHandler
from rich.markup import escape as markup_escape
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.message import Message
from textual.scrollbar import ScrollTo
from textual.widgets import Label, RichLog

from .logging_helper import (
    LogLevelSpec,
    apply_common_logging_cli_args,
    callstack_filter,
    logger_name_filter,
    markup_escape_filter,
    set_log_levels,
    thread_id_filter,
)


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger("trickkiste.base_app")


class RichLogHandler(RichHandler):
    """Redirects rich.RichHanlder capabilities to a textual.RichLog"""

    def __init__(self, widget: RichLog, level: int = logging.INFO):
        super().__init__(show_path=False, markup=True, show_time=False, level=level)
        self.widget: RichLog = widget

    def emit(self, record: logging.LogRecord) -> None:
        record.args = record.args and tuple(
            markup_escape(arg) if isinstance(arg, str) else arg for arg in record.args
        )
        record.msg = markup_escape(record.msg)
        self.widget.write(
            self.render(
                record=record,
                message_renderable=self.render_message(record, self.format(record)),
                traceback=None,
            )
        )


class LockingRichLog(RichLog):
    """A RichLog which turns off autoscroll when scrolling manually"""

    @on(ScrollTo)
    def on_scroll_to(self, _event: Message) -> None:
        """Mandatory comment"""
        self.auto_scroll = self.is_vertical_scroll_end


class TuiBaseApp(App[None]):
    """A nice UI for Sauron stuff"""

    CSS_PATH = Path(__file__).parent / "base_tui_app.css"

    def __init__(
        self,
        logger_show_level: bool = True,
        logger_show_time: bool = True,
        logger_show_name: bool = True,
        logger_show_callstack: bool = False,
        logger_show_funcname: bool = False,
        logger_show_tid: bool = False,
    ) -> None:
        super().__init__()
        self._richlog = LockingRichLog(id="app_log")
        self._logger_show_level = logger_show_level
        self._logger_show_time = logger_show_time
        self._logger_show_name = logger_show_name
        self._logger_show_callstack = logger_show_callstack
        self._logger_show_funcname = logger_show_funcname
        self._logger_show_tid = logger_show_tid
        self._log_level: Sequence[LogLevelSpec] = (logging.INFO,)
        self._footer_label = Label(Text.from_markup("nonsense"), id="footer")

    def add_default_arguments(self, parser: ArgumentParser) -> None:
        """Adds arguments to @parser we need in every app"""
        apply_common_logging_cli_args(parser)

    def compose(self) -> ComposeResult:
        """Set up the UI"""
        yield self._richlog
        yield self._footer_label

    async def on_mount(self) -> None:
        """UI entry point"""
        logging.getLogger().handlers = [handler := RichLogHandler(self._richlog)]

        opt_time = "│ %(asctime)s " if self._logger_show_time else ""
        opt_name = "│ [grey53]%(name)-16s[/] " if self._logger_show_name else ""
        opt_funcname = "│ [grey53]%(funcName)-32s[/] " if self._logger_show_funcname else ""
        opt_callstack = "│ [grey53]%(callstack)-32s[/] " if self._logger_show_callstack else ""
        if self._logger_show_callstack:
            handler.addFilter(callstack_filter)
        opt_tid = "│ [grey53]%(posixTID)-8s[/] " if self._logger_show_tid else ""
        if self._logger_show_tid:
            handler.addFilter(thread_id_filter)
        handler.addFilter(markup_escape_filter)
        handler.addFilter(logger_name_filter)
        handler.setFormatter(
            logging.Formatter(
                "│ %(asctime)s"
                f"{opt_time}{opt_tid}{opt_name}{opt_funcname}{opt_callstack}"
                "│ [bold white]%(message)s[/]",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        self.set_log_levels(*self._log_level)

        if hasattr(self, "initialize"):
            await self.initialize()

    def update_status_bar(self, text: str) -> None:
        """Convenience wrapper - should go to TUIBaseApp"""
        self._footer_label.update(text)

    def execute(self) -> None:
        """Wrapper for async run and optional cleanup if provided"""
        asyncio.run(self.run_async())
        if hasattr(self, "cleanup"):
            self.cleanup()

    def set_log_levels(
        self, *levels: LogLevelSpec, others_level: int | str = logging.WARNING
    ) -> None:
        """Sets the overall log level for internal log console"""
        set_log_levels(*levels, others_level=others_level)
        self._log_level = levels
