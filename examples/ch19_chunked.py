"""Chapter 19: aggregate a 170 MB CSV file in chunks, and compare the peak memory of three strategies."""
import pathlib
import tempfile

import pandas as pd

from pdbook.chunked import make_big_csv, peak_rss_mb, talk_by_caller_chunked, talk_by_caller_whole

with tempfile.TemporaryDirectory() as tmp:
    path = make_big_csv(pathlib.Path(tmp) / "big.csv", times=100)
    size = path.stat().st_size / 1e6
    pd.testing.assert_frame_equal(talk_by_caller_chunked(path), talk_by_caller_whole(path))
    print(f"file {size:.0f} MB; chunked and whole give the same 600 rows")

    base = peak_rss_mb("import pandas, pyarrow")
    strategies = {
        "all 9 columns, whole file": f"import pandas as pd\ndf = pd.read_csv({str(path)!r})",
        "3 columns, whole file": f"from pdbook.chunked import *\nr = talk_by_caller_whole({str(path)!r})",
        "3 columns, 100,000-row chunks": f"from pdbook.chunked import *\nr = talk_by_caller_chunked({str(path)!r})",
    }
    print(f"{'strategy':32s} {'peak MB':>8s}")
    print(f"{'(python and pandas only)':32s} {base:>8.0f}")
    for name, code in strategies.items():
        print(f"{name:32s} {peak_rss_mb(code):>8.0f}")
