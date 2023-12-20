#!/usr/bin/env python3

"""A textual base app with common features like a logging window"""

import asyncio
import logging
from argparse import ArgumentParser
from pathlib import Path

from rich.logging import RichHandler
from rich.markup import escape as markup_escape
from textual import on
from textual.app import App, ComposeResult
from textual.message import Message
from textual.scrollbar import ScrollTo
from textual.widgets import RichLog

from .logging_helper import LOG_LEVELS


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger("trickkiste.base_app")


class RichLogHandler(RichHandler):
    """Redirects rich.RichHanlder capabilities to a textual.RichLog"""

    def __init__(self, widget: RichLog):
        super().__init__(show_path=False, markup=True, show_time=False)
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

    def __init__(self, logger_funcname: bool = True) -> None:
        super().__init__()
        self._richlog = LockingRichLog()
        self._logger_funcname = logger_funcname

    def add_default_arguments(self, parser: ArgumentParser) -> None:
        """Adds arguments to @parser we need in every app"""
        parser.add_argument(
            "--log-level",
            "-l",
            type=str.upper,
            choices=LOG_LEVELS,
            default="INFO",
        )

    def compose(self) -> ComposeResult:
        """Set up the UI"""
        yield self._richlog

    async def on_mount(self) -> None:
        """UI entry point"""
        logging.getLogger().handlers = [handler := RichLogHandler(self._richlog)]
        optional_funcname = "│ [grey53]%(funcName)-32s[/] " if self._logger_funcname else ""
        handler.setFormatter(
            logging.Formatter(
                f"│ %(asctime)s {optional_funcname}│ [bold white]%(message)s[/]",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def execute(self) -> None:
        """Wrapper for async run and optional cleanup if provided"""
        asyncio.run(self.run_async())
        if hasattr(self, "cleanup"):
            self.cleanup()
