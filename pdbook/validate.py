"""Rules that a table of call records must satisfy, and a report of the rows that break them."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

STATUSES = ["answered", "busy", "failed", "noanswer"]
CODECS = ["EVS", "AMR-WB", "AMR-NB"]

EXPECTED_DTYPES = {
    "call_id": "int64", "start": "datetime64[us, UTC]", "caller": "str", "callee": "str",
    "duration_s": "float64", "status": "str", "cell_id": "str", "codec": "str", "roaming": "bool",
}


@dataclass(frozen=True)
class Rule:
    """`violated(df)` returns a boolean Series: True on each row that breaks the rule."""
    name: str
    violated: Callable[[pd.DataFrame], pd.Series]
    severity: str = "error"          # "error" stops the job, "warn" is reported


def check_schema(df: pd.DataFrame, expected: dict[str, str] = EXPECTED_DTYPES) -> list[str]:
    """Problems with the column names and dtypes. An empty list means the schema is as expected."""
    problems = [f"missing column {c}" for c in expected if c not in df.columns]
    problems += [f"unexpected column {c}" for c in df.columns if c not in expected]
    for col, want in expected.items():
        if col in df.columns and str(df[col].dtype) != want:
            problems.append(f"{col}: dtype {df[col].dtype}, expected {want}")
    return problems


def call_rules(subs: pd.DataFrame, cells: pd.DataFrame,
               first: str = "2026-08-31 22:00", last: str = "2026-09-30 22:00") -> list[Rule]:
    """The rules for call records. `first` and `last` bound the start time, in UTC."""
    lo, hi = pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC")
    return [
        Rule("call_id is unique", lambda d: d["call_id"].duplicated(keep="first")),
        Rule("status is one of the four", lambda d: ~d["status"].isin(STATUSES)),
        Rule("duration is not negative", lambda d: d["duration_s"] < 0),
        Rule("an answered call has a duration above 0",
             lambda d: (d["status"] == "answered") & ~(d["duration_s"] > 0)),
        Rule("a call that is not answered has a codec of none",
             lambda d: (d["status"] != "answered") & d["codec"].notna()),
        Rule("callee is in the form +32 and nine digits", lambda d: ~d["callee"].str.match(r"^\+32\d{9}$")),
        Rule("caller is a known subscriber", lambda d: ~d["caller"].isin(subs["subscriber_id"])),
        Rule("start is inside the month", lambda d: ~d["start"].between(lo, hi)),
        Rule("cell is known when it is present",
             lambda d: d["cell_id"].notna() & ~d["cell_id"].isin(cells["cell_id"])),
        Rule("a call has a cell", lambda d: d["cell_id"].isna(), severity="warn"),
    ]


def validate(df: pd.DataFrame, rules: list[Rule]) -> pd.DataFrame:
    """One row for each rule: how many rows break it, their share, and the first three labels."""
    rows = []
    for rule in rules:
        bad = rule.violated(df).fillna(False).astype(bool)
        rows.append({
            "rule": rule.name,
            "severity": rule.severity,
            "violations": int(bad.sum()),
            "share": round(float(bad.mean()), 5),
            "first_rows": df.index[bad][:3].tolist(),
        })
    return pd.DataFrame(rows)


def assert_valid(report: pd.DataFrame) -> None:
    """Raise ValueError when a rule of severity "error" has violations."""
    failed = report[(report["severity"] == "error") & (report["violations"] > 0)]
    if len(failed):
        lines = [f"{r.rule}: {r.violations}" for r in failed.itertuples()]
        raise ValueError("data validation failed:\n  " + "\n  ".join(lines))


def plant_faults(df: pd.DataFrame, seed: int = 0) -> tuple[pd.DataFrame, dict[str, int]]:
    """Copy `df` and break it in six ways on disjoint rows.

    Returns the copy and the number of violations that each rule of `call_rules` must report.
    The numbers are exact, so the validator is measured: it must find these and no others.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    out = df.copy()
    answered = out.index[(out["status"] == "answered")].to_numpy()
    other = out.index[(out["status"] != "answered")].to_numpy()
    pick = rng.permutation(answered[1:])           # row 0 stays: it is the original of the repeats
    other_pick = rng.permutation(other)

    repeat, negative, no_duration, bad_caller, bad_callee, bad_start = (
        pick[0:7], pick[7:12], pick[12:18], pick[18:22], pick[22:25], pick[25:27])
    coded = other_pick[0:4]

    out.loc[repeat, "call_id"] = out["call_id"].iloc[0]
    out.loc[negative, "duration_s"] = -1.0
    out.loc[no_duration, "duration_s"] = np.nan
    out.loc[bad_caller, "caller"] = "S9999"
    out.loc[bad_callee, "callee"] = "0477123456"
    out.loc[bad_start, "start"] = pd.Timestamp("2025-01-01", tz="UTC")
    out.loc[coded, "codec"] = "EVS"

    expected = {
        "call_id is unique": 7,
        "duration is not negative": 5,
        "an answered call has a duration above 0": 5 + 6,     # a negative duration is not above 0
        "a call that is not answered has a codec of none": 4,
        "callee is in the form +32 and nine digits": 3,
        "caller is a known subscriber": 4,
        "start is inside the month": 2,
    }
    return out, expected
