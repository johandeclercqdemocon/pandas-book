"""Chapter 12: hourly KPIs in local time, and the 25-hour day."""
import pandas as pd

from pdbook.io import load_kpi
from pdbook.kpi import hourly_kpi

kpi = load_kpi()
hourly = hourly_kpi(kpi)
print(f"raw rows {len(kpi):,d} -> unique {len(kpi.drop_duplicates(['ts', 'cell_id'])):,d} -> hourly rows {len(hourly):,d}")
day = hourly[hourly["ts"].dt.strftime("%Y-%m-%d") == "2026-10-25"]
print("hours on 2026-10-25 for each cell:", day.groupby("cell_id").size().unique().tolist())
print("samples kept:", int(hourly["n"].sum()), "complete hours:", int(hourly["complete"].sum()), "of", len(hourly))
