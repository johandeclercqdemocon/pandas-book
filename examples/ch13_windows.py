"""Chapter 13: flag spikes in the cell KPIs, and score the flags against the known spike."""
import pandas as pd

from pdbook.io import load_kpi
from pdbook.spikes import flag_spikes

kpi = load_kpi().drop_duplicates(["ts", "cell_id"]).reset_index(drop=True)
truth = (kpi["cell_id"] == "BRU-002") & kpi["ts"].between("2026-10-25 14:00", "2026-10-25 14:30")
print(f"{'z':>3s} {'found':>6s} {'false':>6s} {'flagged':>8s}   (the injected spike has {int(truth.sum())} samples)")
for z in (2, 3, 4, 5, 8):
    f = flag_spikes(kpi, z=z)
    print(f"{z:>3d} {int((f & truth).sum()):>6d} {int((f & ~truth).sum()):>6d} {int(f.sum()):>8d}")
