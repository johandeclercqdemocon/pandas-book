"""What an index promises: is it unique, sorted, named, and what type are its labels?"""
from __future__ import annotations

import pandas as pd


def index_audit(df: pd.DataFrame) -> dict[str, object]:
    idx = df.index
    return {
        "levels": idx.nlevels,
        "names": list(idx.names),
        "dtype": str(idx.dtype) if idx.nlevels == 1 else [str(d) for d in idx.dtypes],
        "unique": bool(idx.is_unique),
        "sorted": bool(idx.is_monotonic_increasing),
        "duplicate_labels": int(idx.duplicated().sum()),
        "has_missing": bool(idx.to_frame(index=False).isna().any().any()),  # MultiIndex has no isna()
    }
