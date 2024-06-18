#!/usr/bin/env python3

"""Too lazy for a real test - I'm using this example to check if colorful logging works"""

import asyncio
import logging

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Tree

from trickkiste.base_tui_app import TuiBaseApp


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger("trickkiste.fancytui")


class ExampleTUI(TuiBaseApp):
    """A little example TUI"""

    def __init__(self) -> None:
        super().__init__(logger_show_funcname=True, logger_show_tid=True, logger_show_name=True)
        self.tree_widget: Tree[None] = Tree("A Tree")

    async def initialize(self) -> None:
        """UI entry point"""
        self.set_log_levels((log(), "DEBUG"), ("trickkiste", "INFO"), others_level="WARNING")
        self.produce()

    def compose(self) -> ComposeResult:
        """Set up the UI"""
        yield self.tree_widget
        yield from super().compose()

    @on(Tree.NodeSelected)
    def on_node_selected(self, event: Tree.NodeSelected[None]) -> None:
        """React on clicking a node (links handled differently)"""
        log().debug("clicked %s", event.node.label)

    @work(exit_on_error=True)
    async def produce(self) -> None:
        """Busy worker task continuously rebuilding the job tree"""
        log().info("first message from async worker")
        cpu_node = self.tree_widget.root.add("CPU")
        mem_node = self.tree_widget.root.add("MEM")
        disk_node = self.tree_widget.root.add("DISK")
        self.tree_widget.root.expand()
        while True:
            log().info("step..")
            cpu_node.set_label("TBD")
            mem_node.set_label("TBD")
            disk_node.set_label("TBD")
            self.log_foo()
            await asyncio.sleep(15)

    @work(exit_on_error=True, thread=True)
    def log_foo(self) -> None:
        """Some function executed in a separate thread"""
        log().info("foo")


if __name__ == "__main__":
    ExampleTUI().execute()
