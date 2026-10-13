"""Chapter 2: read the call records correctly, and compare file formats."""
import pathlib
import tempfile
import time

import pandas as pd

from pdbook.io import load_calls

raw = pd.read_csv("data/calls.csv")
calls = load_calls()
print("naive read :", dict(raw.dtypes.astype(str))["callee"], "|", dict(raw.dtypes.astype(str))["start"])
print("loader     :", dict(calls.dtypes.astype(str))["callee"], "|", dict(calls.dtypes.astype(str))["start"])

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    calls.to_csv(tmp / "calls.csv", index=False)
    calls.to_parquet(tmp / "calls.parquet")
    calls.to_json(tmp / "calls.jsonl", orient="records", lines=True, date_format="iso")
    print()
    print(f"{'format':10s} {'bytes':>10s}  {'read ms':>8s}  round trip equal")
    for name, read in [
        ("csv", lambda p: pd.read_csv(p, dtype={"caller": "str", "callee": "str"}, parse_dates=["start"])),
        ("parquet", pd.read_parquet),
        ("jsonl", lambda p: pd.read_json(p, lines=True, dtype={"caller": "str", "callee": "str"}, convert_dates=["start"])),
    ]:
        path = next(tmp.glob(f"calls.{'jsonl' if name == 'jsonl' else name}"))
        t0 = time.perf_counter()
        back = read(path)
        ms = (time.perf_counter() - t0) * 1000
        try:
            pd.testing.assert_frame_equal(calls, back)
            same = "yes"
        except AssertionError as e:
            same = "no: " + str(e).splitlines()[0][:50]
        print(f"{name:10s} {path.stat().st_size:>10,d}  {ms:>8.1f}  {same}")
