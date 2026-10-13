"""Chapter 3: five operations questions, each answered by one selection."""
import pandas as pd

from pdbook.io import load_calls


def ops_questions(calls: pd.DataFrame) -> dict[str, int]:
    answered = calls["status"] == "answered"
    return {
        "answered, over 10 min, Brussels cell":
            int((answered & (calls["duration_s"] > 600) & calls["cell_id"].str.startswith("BRU")).sum()),
        "answered, no cell recorded":
            int((answered & calls["cell_id"].isna()).sum()),
        "failed while roaming":
            int((calls["roaming"] & (calls["status"] == "failed")).sum()),
        "wideband or EVS codec":
            int(calls["codec"].isin(["EVS", "AMR-WB"]).sum()),
        "started on 10 September (UTC)":
            int(calls["start"].between(pd.Timestamp("2026-09-10", tz="UTC"),
                                       pd.Timestamp("2026-09-11", tz="UTC"), inclusive="left").sum()),
    }


if __name__ == "__main__":
    for name, n in ops_questions(load_calls()).items():
        print(f"{n:>7,d}  {name}")
