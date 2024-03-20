#!/usr/bin/env python3

"""Mixed common stuff not big enough for a separate module"""

import hashlib
import logging
import os
import re
import shlex
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from datetime import datetime
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


def dur_str(seconds: float, fixed: bool = False) -> str:
    """Turns a duration defined by @seconds into a string like '1d:2h:3m'
    If @fixed is True, numbers will be 0-padded for uniform width.
    Negative values for @seconds are not supported (yet)
    >>> dur_str(42)
    '42s'
    >>> dur_str(12345)
    '3h:25m:45s'
    """
    if not fixed and not seconds:
        return "0s"
    digits = 2 if fixed else 1
    days = f"{seconds//86400:0{digits}d}d" if fixed or seconds >= 86400 else ""
    hours = (
        f"{seconds//3600%24:0{digits}d}h" if fixed or seconds >= 3600 and (seconds % 86400) else ""
    )
    minutes = f"{seconds//60%60:0{digits}d}m" if fixed or seconds >= 60 and (seconds % 3600) else ""
    seconds_str = (
        f"{seconds%60:0{digits}d}s" if not fixed and ((seconds % 60) or seconds == 0) else ""
    )
    return ":".join(e for e in (days, hours, minutes, seconds_str) if e)


def age_str(now: float | datetime, age: None | int | datetime, fixed: bool = False) -> str:
    """Turn a number of seconds into something human readable
    >>> age_str(1700000000, 1600000000)
    '1157d:9h:46m:40s'
    """
    if age is None:
        return "--"
    age_ts = age.timestamp() if isinstance(age, datetime) else age
    now_ts = now.timestamp() if isinstance(now, datetime) else now
    if (age_ts or now_ts) <= 0.0:
        return "--"
    return dur_str(now_ts - age_ts, fixed=fixed)


def date_str(timestamp: int | datetime, datefmt: str = "%Y.%m.%d-%H:%M:%S") -> str:
    """Returns a uniform time string from a timestamp or a datetime
    >>> date_str(datetime.strptime("1980.01.04-12:55:02", "%Y.%m.%d-%H:%M:%S"))
    '1980.01.04-12:55:02'
    """
    if not timestamp:
        return "--"
    date_dt = timestamp if isinstance(timestamp, datetime) else datetime.fromtimestamp(timestamp)
    if date_dt.year < 1000:
        return "--"
    return (date_dt).strftime(datefmt)


def parse_age(string: str) -> int:
    """Return seconds extracted from something parsable as an age ('3d:4h')
    >>> parse_age("3600")
    3600
    >>> parse_age("3h")
    10800
    >>> parse_age("1d:10h")
    122400
    >>> parse_age("1d10h")
    122400
    >>> parse_age("1.5d")
    129600
    """
    number = r"\d*(?:\.(?:\d*)?)?"
    with suppress(ValueError):
        return int(string)
    if match := re.match(
        (
            "(?i)^"
            f"(?:({number})d)?"
            "(?::)?"
            f"(?:({number})h)?"
            "(?::)?"
            f"(?:({number})m)?"
            "(?::)?"
            f"(?:({number})s)?$"
        ),
        string,
    ):
        days, hours, mins, secs = match.groups()
        return int(
            float(days or "0") * 86400
            + float(hours or "0") * 3600
            + float(mins or "0") * 60
            + float(secs or "0")
        )
    raise ValueError(f"Cannot turn {string!r} into duration")


def smart_split(string: str, delimiter: str = ",") -> Iterator[str]:
    """Like str.split but takes quotes and parenthesis into account
    >>> list(smart_split("(=,),'a=x',\\"b=y\\""))
    ['(=,)', "'a=x'", '"b=y"']
    """
    splits: list[int] = []
    closers: list[str] = []
    parenthizers = {'"': '"', "'": "'", "[": "]", "(": ")"}
    for i, char in enumerate(string):
        if char == delimiter and not closers:
            splits.append(i)
        elif closers and char == closers[-1]:
            closers.pop()
        elif char in parenthizers:
            closers.append(parenthizers[char])
    start = 0
    for pos in splits:
        yield string[start:pos]
        start = pos + 1
    yield string[start:]


def split_params(string: str) -> Mapping[str, str]:
    """Splits a 'string packed map' into a dict
    >>> split_params("foo=23,bar=42,true='pi=3,14'")
    {'foo': '23', 'bar': '42', 'true': "'pi=3,14'"}
    """
    return {k: v for p in smart_split(string, ",") if p for k, v in (p.split("=", 1),)}


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
