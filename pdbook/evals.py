"""Compare two configurations of a system on the same tasks."""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

from pdbook.datasets import DATA


def load_runs(path: str | pathlib.Path | None = None) -> pd.DataFrame:
    """One row for each (task, config, seed). The nested `tokens` object becomes two columns."""
    path = DATA / "runs.jsonl" if path is None else path
    with open(path, encoding="utf-8") as f:
        return pd.json_normalize([json.loads(line) for line in f if line.strip()])


def compare_configs(runs: pd.DataFrame, a: str = "baseline", b: str = "improved",
                    n_boot: int = 2000, seed: int = 0) -> dict[str, float]:
    """Pass rates, the paired difference b - a, and 95% intervals for the difference.

    The unit of the bootstrap is the task: the seeds of one task are averaged first, then tasks
    are resampled. `unpaired_se` treats the 450 runs of each config as independent samples.
    """
    per_task = runs.groupby(["task_id", "config"])["passed"].mean().unstack()
    diff = (per_task[b] - per_task[a]).to_numpy()
    rng = np.random.default_rng(seed)
    boots = rng.choice(diff, size=(n_boot, len(diff)), replace=True).mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    pa = runs.loc[runs["config"] == a, "passed"].astype(float)
    pb = runs.loc[runs["config"] == b, "passed"].astype(float)
    unpaired_se = float(np.sqrt(pa.var() / len(pa) + pb.var() / len(pb)))
    return {
        "tasks": float(len(diff)), "rate_a": float(pa.mean()), "rate_b": float(pb.mean()),
        "diff": float(diff.mean()), "paired_se": float(diff.std(ddof=1) / np.sqrt(len(diff))),
        "unpaired_se": unpaired_se, "ci_low": float(lo), "ci_high": float(hi),
        "tasks_better": float((diff > 0).sum()), "tasks_worse": float((diff < 0).sum()),
    }
