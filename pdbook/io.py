"""One place that knows how each file in data/ must be read.

Every chapter after Chapter 2 loads data through these functions, so a change of format is a
change in one file. Each function takes `path=None`, which means the file in `data/`.
"""
from __future__ import annotations

import pathlib

import pandas as pd

from pdbook.datasets import DATA


def _path(path: str | pathlib.Path | None, name: str) -> str | pathlib.Path:
    return DATA / name if path is None else path


def load_calls(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    """Call records. `start` is a timezone-aware UTC timestamp; phone numbers are text.

    Identifiers are text: read_csv would turn "+32434086075" into the integer 32434086075.
    """
    return pd.read_csv(_path(path, "calls.csv"), dtype={"caller": "str", "callee": "str"},
                       parse_dates=["start"])


def load_subscribers(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    return pd.read_csv(_path(path, "subscribers.csv"), dtype={"msisdn": "str"}, parse_dates=["signup_date"])


def load_cells(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    return pd.read_csv(_path(path, "cells.csv"))


def load_plans(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    return pd.read_csv(_path(path, "plans.csv"))


def load_kpi(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    return pd.read_csv(_path(path, "kpi.csv"), parse_dates=["ts"])
