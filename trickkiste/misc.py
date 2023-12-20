#!/usr/bin/env python3

"""Mixed common stuff not big enough for a separate module"""

import hashlib
import logging
import os
import shlex
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from subprocess import DEVNULL, check_output


def log() -> logging.Logger:
    """Returns the logger instance to use here"""
    return logging.getLogger("trickkiste.misc")


def md5from(filepath: Path) -> None | str:
    """Returns an MD5 sum from contents of file provided"""
    with suppress(FileNotFoundError):
        with open(filepath, "rb") as input_file:
            file_hash = hashlib.md5()
            while chunk := input_file.read(1 << 16):
                file_hash.update(chunk)
            return file_hash.hexdigest()
    return None


@contextmanager
def cwd(path: Path) -> Iterator[None]:
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def dur_str(seconds: int) -> str:
    """Turns a number of seconds into a string like 1d:2h:3m"""
    if not seconds:
        return "0s"
    days = f"{seconds//86400:d}d" if seconds >= 86400 else ""
    hours = f"{seconds//3600%24:d}h" if seconds >= 3600 and (seconds % 86400) else ""
    minutes = f"{seconds//60%60:d}m" if 86400 > seconds and (seconds % 3600) else ""
    return ":".join(e for e in (days, hours, minutes) if e)


def split_params(string: str) -> Mapping[str, str]:
    """Splits a 'string packed map' into a dict
    >>> split_params("foo=23,bar=42")
    {'foo': '23', 'bar': '42'}
    """
    return {k: v for p in string.split(",") if p for k, v in (p.split("="),)}


def compact_dict(
    mapping: Mapping[str, float | str], *, maxlen: None | int = 10, delim: str = ", "
) -> str:
    """Turns a dict into a 'string packed map' (for making a dict human readable)
    >>> compact_dict({'foo': '23', 'bar': '42'})
    'foo=23, bar=42'
    """

    def short(string: str) -> str:
        return string if maxlen is None or len(string) <= maxlen else f"{string[:maxlen-2]}.."

    return delim.join(
        f"{k}={short_str}" for k, v in mapping.items() if (short_str := short(str(v)))
    )


def process_output(cmd: str) -> str:
    """Return command output as one blob"""
    return check_output(shlex.split(cmd), stderr=DEVNULL, text=True)
