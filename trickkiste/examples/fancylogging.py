#!/usr/bin/env python3

"""Too lazy for a real test - I'm using this example to check if colorful logging works"""

import logging

from trickkiste.logging_helper import setup_logging


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger("trickkiste.example_logging")


def main() -> None:
    """Runs this"""
    setup_logging(log(), level=logging.DEBUG)

    log().debug("debug message")
    log().info("debug message")


if __name__ == "__main__":
    main()
