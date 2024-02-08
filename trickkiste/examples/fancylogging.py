#!/usr/bin/env python3

"""Example for fancy logging"""

import logging
from argparse import ArgumentParser

from trickkiste.logging_helper import apply_common_logging_cli_args, setup_logging


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger(__name__)


def main() -> None:
    """Runs this"""
    parser = ArgumentParser(__doc__)
    apply_common_logging_cli_args(parser)
    args = parser.parse_args()

    setup_logging(log(), level=args.log_level)

    log().debug("debug message")
    log().info("info message")
    log().warning("warning message")
    log().error("error message")

    logging.getLogger("other.module").debug("only shown with level=ALL_DEBUG")
    logging.getLogger("other.module").info("only shown with level=ALL_DEBUG")
    logging.getLogger("other.module").warning("this is visible")
    logging.getLogger("other.module").error("this is also visible")


if __name__ == "__main__":
    main()
