#!/usr/bin/env python3

"""A textual base app with common features like a logging window"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-locals
# pylint: disable=too-many-arguments
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes

import asyncio
import logging
from argparse import ArgumentParser
from collections.abc import MutableSequence, Sequence
from pathlib import Path

from rich.color import Color
from rich.console import Console, ConsoleOptions, RenderResult
from rich.logging import RichHandler
from rich.markup import escape as markup_escape
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.message import Message
from textual.renderables._blend_colors import blend_colors
from textual.renderables.sparkline import Sparkline as SparklineRenderable
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
        logger_show_name: bool | int = True,
        logger_show_callstack: bool | int = False,
        logger_show_funcname: bool | int = False,
        logger_show_tid: bool | int = False,
        logger_max_lines: int | bool = 10_000,
    ) -> None:
        def bool_to_int(val: int | bool, default: int) -> int:
            if not val:
                return 0
            if val is True:
                return default
            return val

        super().__init__()
        self._richlog = LockingRichLog(id="app_log")
        self._richlog.max_lines = logger_max_lines or None
        self._richlog.can_focus = False
        self._logger_show_level = logger_show_level
        self._logger_show_time = logger_show_time
        self._logger_width_name = bool_to_int(logger_show_name, 16)
        self._logger_width_callstack = bool_to_int(logger_show_callstack, 32)
        self._logger_width_funcname = bool_to_int(logger_show_funcname, 20)
        self._logger_width_tid = bool_to_int(logger_show_tid, 8)
        self._log_level: Sequence[LogLevelSpec] = (logging.INFO,)
        self._footer_label = Label(Text.from_markup("nonsense"), id="footer")

    def add_default_arguments(self, parser: ArgumentParser) -> ArgumentParser:
        """Adds arguments to @parser we need in every app"""
        apply_common_logging_cli_args(parser)
        return parser

    def compose(self) -> ComposeResult:
        """Set up the UI"""
        yield self._richlog
        yield self._footer_label

    async def on_mount(self) -> None:
        """UI entry point"""
        logging.getLogger().handlers = [handler := RichLogHandler(self._richlog)]

        opt_time = "│ %(asctime)s " if self._logger_show_time else ""
        opt_name = (
            f"│ [grey53]%(name)-{self._logger_width_name}s[/] " if self._logger_width_name else ""
        )
        opt_funcname = (
            f"│ [grey53]%(funcName)-{self._logger_width_funcname}s[/] "
            if self._logger_width_funcname
            else ""
        )
        opt_callstack = (
            f"│ [grey53]%(callstack)-{self._logger_width_callstack}s[/] "
            if self._logger_width_callstack
            else ""
        )
        if self._logger_width_callstack:
            handler.addFilter(callstack_filter)
        opt_tid = (
            f"│ [grey53]%(posixTID)-{self._logger_width_tid}s[/] " if self._logger_width_tid else ""
        )
        if self._logger_width_tid:
            handler.addFilter(thread_id_filter)
        handler.addFilter(markup_escape_filter)
        handler.addFilter(logger_name_filter)
        handler.setFormatter(
            logging.Formatter(
                f"{opt_time}{opt_tid}{opt_name}{opt_funcname}{opt_callstack}"
                "│ [bold white]%(message)s[/]",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        self.set_log_levels(*self._log_level)

        await self.initialize()

    async def initialize(self) -> None:
        """Not implemented"""

    def update_status_bar(self, text: str) -> None:
        """Convenience wrapper - should go to TUIBaseApp"""
        self._footer_label.update(text)

    def execute(self) -> None:
        """Wrapper for async run and optional cleanup if provided"""
        asyncio.run(self.run_async())
        self.cleanup()

    def cleanup(self) -> None:
        """Not implemented"""

    def set_log_levels(
        self, *levels: LogLevelSpec, others_level: int | str = logging.WARNING
    ) -> None:
        """Sets the overall log level for internal log console"""
        set_log_levels(*levels, others_level=others_level)
        self._log_level = levels


class HeatBar(SparklineRenderable[float]):
    """SparklineRenderable with additional features"""

    BARS = "▁▂▃▄▅▆▇█"
    BARS_INVERTED = " 🮂🮃🮄🮅🮆█"

    def __init__(
        self,
        *,
        width: int | None = 10,
        min_color: int | str | Color = Color.from_rgb(0, 255, 0),
        max_color: int | str | Color = Color.from_rgb(255, 0, 0),
        min_bar_value: float | None = None,
        max_bar_value: float | None = None,
        min_color_value: float | None = None,
        max_color_value: float | None = None,
        inverted: bool = False,
    ) -> None:
        super().__init__(
            data=[],
            width=width,
            min_color=(
                Color.from_triplet(Color.from_ansi(min_color).get_truecolor())
                if isinstance(min_color, int)
                else (
                    Color.from_triplet(Color.parse(min_color).get_truecolor())
                    if isinstance(min_color, str)
                    else min_color
                )
            ),
            max_color=(
                Color.from_triplet(Color.from_ansi(max_color).get_truecolor())
                if isinstance(max_color, int)
                else (
                    Color.from_triplet(Color.parse(max_color).get_truecolor())
                    if isinstance(max_color, str)
                    else max_color
                )
            ),
        )
        self.data: MutableSequence[float] = []
        self.bars = self.BARS_INVERTED if inverted else self.BARS
        self.inverted = inverted
        self.min_bar_value = min_bar_value
        self.max_bar_value = max_bar_value
        self.min_color_value = min_color_value
        self.max_color_value = max_color_value

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        width = self.width or options.max_width
        len_data = len(self.data)
        if len_data == 0:
            yield Segment("▁" * width, self.min_color)
            return
        if len_data == 1:
            yield Segment("█" * width, self.max_color)
            return

        minimum = min(self.data) if self.min_bar_value is None else self.min_bar_value
        maximum = max(self.data) if self.max_bar_value is None else self.max_bar_value

        extent = maximum - minimum or 1

        buckets = tuple(self._buckets(list(self.data), num_buckets=width))

        bucket_index = 0.0
        bars_rendered = 0
        step = len(buckets) / width
        summary_function = self.summary_function
        min_color, max_color = self.min_color.color, self.max_color.color
        assert min_color is not None
        assert max_color is not None
        while bars_rendered < width:
            partition = buckets[int(bucket_index)]
            partition_summary = summary_function(partition)
            height_ratio = (partition_summary - minimum) / extent
            bar_index = int(height_ratio * (len(self.bars) - 1))
            bar_color = blend_colors(min_color, max_color, height_ratio)
            bars_rendered += 1
            bucket_index += step
            yield Segment(
                self.bars[min(bar_index, len(self.bars) - 1)], Style.from_color(bar_color)
            )
