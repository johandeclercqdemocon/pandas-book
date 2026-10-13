"""Aggregate a CSV file that is read in chunks, and measure the memory of a strategy."""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pandas as pd

from pdbook.bench import replicate
from pdbook.io import load_calls


def make_big_csv(path: str | pathlib.Path, times: int = 50) -> pathlib.Path:
    """Write the call records `times` over to `path` (50 times: 1,000,000 rows, 84 MB)."""
    path = pathlib.Path(path)
    replicate(load_calls(), times).to_csv(path, index=False)
    return path


def talk_by_caller_chunked(path: str | pathlib.Path, chunksize: int = 100_000) -> pd.DataFrame:
    """Sum and count of the duration of answered calls for each caller, with bounded memory.

    Only the columns that are needed are read. Each chunk is reduced to one row for each
    caller, and the reduced chunks are added. Sum and count can be added across chunks;
    a mean is computed at the end as sum / count.
    """
    total = None
    reader = pd.read_csv(path, usecols=["caller", "status", "duration_s"],
                         dtype={"caller": "str"}, chunksize=chunksize)
    for chunk in reader:
        part = chunk[chunk["status"] == "answered"].groupby("caller")["duration_s"].agg(["sum", "size"])
        total = part if total is None else total.add(part, fill_value=0)
    assert total is not None
    # add(fill_value=0) returns floats when a caller is absent from a chunk. A count is an integer.
    total["size"] = total["size"].astype("int64")
    total["mean"] = total["sum"] / total["size"]
    return total.sort_index()


def talk_by_caller_whole(path: str | pathlib.Path) -> pd.DataFrame:
    """The same result, with the whole file in memory."""
    df = pd.read_csv(path, usecols=["caller", "status", "duration_s"], dtype={"caller": "str"})
    out = df[df["status"] == "answered"].groupby("caller")["duration_s"].agg(["sum", "size"])
    out["mean"] = out["sum"] / out["size"]
    return out.sort_index()


def peak_rss_mb(code: str) -> float:
    """Peak resident memory, in MB, of a fresh Python process that runs `code`. Linux only.

    The figure is VmHWM from /proc/self/status, the high-water mark of the new process.
    `resource.getrusage(...).ru_maxrss` is not used: a child inherits the peak of the parent
    at fork, so it reports the memory of the caller, not of `code`.
    The result includes the memory of Python and the imported packages (about 200 MB here).
    """
    wrapper = (code + "\n"
               "for line in open('/proc/self/status'):\n"
               "    if line.startswith('VmHWM:'):\n"
               "        print(int(line.split()[1]) / 1024)\n")
    out = subprocess.run([sys.executable, "-c", wrapper], capture_output=True, text=True, check=True,
                         env={"PYTHONPATH": str(pathlib.Path(__file__).resolve().parent.parent), "PATH": ""})
    return float(out.stdout.strip().splitlines()[-1])
