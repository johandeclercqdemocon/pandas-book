"""Deterministic datasets for the book.

    uv run python -m pdbook.datasets        # rewrites data/

The files in data/ ship with the book. Every number in the text comes from those files, not from
this generator. Regenerating with another numpy version can change the bytes (numpy does not
promise one random stream for ever), so `scripts/verify_claims.py` pins the SHA-256 of each file.

The data describe a small mobile operator in Belgium: subscribers, plans, cells, call records,
5-minute cell KPIs, call traces, a messy contact export and the results of an evaluation run.
All of it is synthetic.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED = 20261012

CITY_CENTER = {"Brussels": (50.85, 4.35), "Antwerp": (51.22, 4.40), "Ghent": (51.05, 3.72),
               "Liège": (50.63, 5.57), "Leuven": (50.88, 4.70)}
CELLS_PER_CITY = {"Brussels": 4, "Antwerp": 3, "Ghent": 2, "Liège": 2, "Leuven": 1}
PLANS = pd.DataFrame({
    "plan": ["prepaid", "basic", "plus", "business"],
    "monthly_fee_eur": [0.0, 12.5, 24.0, 45.0],
    "included_minutes": [0, 100, 500, 2000],
    "rate_per_min_eur": [0.15, 0.10, 0.06, 0.04],
})


def _rng(k: int) -> np.random.Generator:
    return np.random.default_rng([SEED, k])


def cells() -> pd.DataFrame:
    rng = _rng(1)
    rows = []
    for city, n in CELLS_PER_CITY.items():
        lat0, lon0 = CITY_CENTER[city]
        for i in range(1, n + 1):
            rows.append({"cell_id": f"{city[:3].upper()}-{i:03d}", "city": city,
                         "lat": round(lat0 + rng.normal(0, 0.02), 5),
                         "lon": round(lon0 + rng.normal(0, 0.03), 5),
                         "tech": "5G" if rng.random() < 0.35 else "4G"})
    return pd.DataFrame(rows)


def subscribers() -> pd.DataFrame:
    rng = _rng(2)
    n = 600
    city = rng.choice(list(CITY_CENTER), size=n, p=[0.35, 0.25, 0.15, 0.15, 0.10])
    plan = rng.choice(PLANS["plan"], size=n, p=[0.30, 0.35, 0.25, 0.10])
    signup = pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.integers(0, 365 * 8 + 240, size=n), unit="D")
    digits = rng.integers(10_000_000, 99_999_999, size=n)
    return pd.DataFrame({
        "subscriber_id": [f"S{i:04d}" for i in range(1, n + 1)],
        "msisdn": [f"+324{d}" for d in digits],
        "plan": plan,
        "city": city,
        "signup_date": signup.strftime("%Y-%m-%d"),
        "active": rng.random(n) < 0.92,
    })


def calls(subs: pd.DataFrame, cell_table: pd.DataFrame) -> pd.DataFrame:
    rng = _rng(3)
    n = 20_000
    days = pd.date_range("2026-09-01", periods=30, freq="D")
    day_w = np.where(days.dayofweek < 5, 1.0, 0.55)
    day = rng.choice(30, size=n, p=day_w / day_w.sum())
    hour_w = np.array([1, 1, 1, 1, 1, 2, 4, 8, 12, 14, 14, 12, 10, 11, 13, 14, 13, 12, 14, 15, 12, 8, 5, 2], float)
    hour = rng.choice(24, size=n, p=hour_w / hour_w.sum())
    second = rng.integers(0, 3600, size=n)
    local = days[day] + pd.to_timedelta(hour * 3600 + second, unit="s")
    start = pd.Series(local).dt.tz_localize("Europe/Brussels").dt.tz_convert("UTC")
    order = np.argsort(start.to_numpy(), kind="stable")
    start = start.iloc[order].reset_index(drop=True)

    rank_w = 1.0 / np.arange(1, len(subs) + 1) ** 0.6
    rng.shuffle(rank_w)
    caller_ix = rng.choice(len(subs), size=n, p=rank_w / rank_w.sum())
    caller = subs["subscriber_id"].to_numpy()[caller_ix]
    on_net = rng.random(n) < 0.30
    external = np.array([f"+324{d}" for d in rng.integers(10_000_000, 99_999_999, size=n)])
    callee = np.where(on_net, subs["msisdn"].to_numpy()[rng.integers(0, len(subs), size=n)], external)

    status = rng.choice(["answered", "noanswer", "busy", "failed"], size=n, p=[0.78, 0.10, 0.07, 0.05])
    dur = np.clip(np.exp(rng.normal(np.log(80), 1.0, size=n)), 1, 7200).round().astype(float)
    dur = np.where(status == "answered", dur, np.where(status == "failed", np.nan, 0.0))

    home = subs["city"].to_numpy()[caller_ix]
    cells_by_city = {c: g["cell_id"].to_numpy() for c, g in cell_table.groupby("city")}
    all_cells = cell_table["cell_id"].to_numpy()
    cell = np.empty(n, dtype=object)
    for i in range(n):
        pool = cells_by_city[home[i]] if rng.random() < 0.85 else all_cells
        cell[i] = pool[rng.integers(0, len(pool))]
    cell = pd.Series(cell)
    cell[rng.random(n) < 0.015] = None

    tech = cell_table.set_index("cell_id")["tech"]
    is5g = cell.map(tech).eq("5G").to_numpy()
    u = rng.random(n)
    codec = np.where(is5g, np.where(u < 0.6, "EVS", np.where(u < 0.9, "AMR-WB", "AMR-NB")),
                     np.where(u < 0.1, "EVS", np.where(u < 0.7, "AMR-WB", "AMR-NB")))
    codec = pd.Series(codec).where(status == "answered", None)

    df = pd.DataFrame({
        "call_id": np.arange(1, n + 1),
        "start": start.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "caller": caller,
        "callee": callee,
        "duration_s": dur,
        "status": status,
        "cell_id": cell,
        "codec": codec,
        "roaming": rng.random(n) < 0.03,
    })
    # Late-arriving records: 1000 rows are appended at the end of the file, out of time order.
    late = np.sort(rng.choice(n, size=1000, replace=False))
    keep = np.setdiff1d(np.arange(n), late)
    return pd.concat([df.iloc[keep], df.iloc[late]], ignore_index=True)


def kpi(cell_table: pd.DataFrame) -> pd.DataFrame:
    rng = _rng(4)
    ts = pd.date_range("2026-10-24 00:00", "2026-10-26 23:55", freq="5min", tz="UTC")
    rows = []
    for cid in cell_table["cell_id"].iloc[:6]:
        local_hour = (ts.tz_convert("Europe/Brussels").hour + ts.minute / 60).to_numpy()
        base = 45 + 30 * np.sin((local_hour - 11) / 24 * 2 * np.pi) + rng.normal(0, 4, len(ts))
        util = np.clip(base + rng.normal(0, 3), 2, 99).round(1)
        drop = np.clip(0.4 + 0.004 * util + rng.normal(0, 0.08, len(ts)), 0, None).round(2)
        thr = np.clip(120 - 0.9 * util + rng.normal(0, 6, len(ts)), 5, None).round(1)
        rows.append(pd.DataFrame({"ts": ts, "cell_id": cid, "prb_util_pct": util,
                                  "drop_rate_pct": drop, "throughput_mbps": thr}))
    df = pd.concat(rows, ignore_index=True)
    spike = (df["cell_id"] == "BRU-002") & df["ts"].between("2026-10-25 14:00", "2026-10-25 14:30")
    df.loc[spike, "drop_rate_pct"] = rng.uniform(8, 12, spike.sum()).round(2)
    outage = (df["cell_id"] == "BRU-004") & df["ts"].between("2026-10-25 10:00", "2026-10-25 11:55")
    df = df[~outage]
    df = df[rng.random(len(df)) > 0.015]
    df = df.sort_values(["ts", "cell_id"]).reset_index(drop=True)
    dup = df.iloc[rng.choice(len(df), size=25, replace=False)]
    df = pd.concat([df, dup]).sort_values(["ts", "cell_id"], kind="stable").reset_index(drop=True)
    df["ts"] = df["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def messy_contacts() -> pd.DataFrame:
    rng = _rng(5)
    first = ["An", "Bram", "Chloé", "Dirk", "Eline", "Farid", "Greet", "Hugo", "Ines", "Jan", "Karim",
             "Lotte", "Maarten", "Nadia", "Omar", "Petra", "Quinten", "Rik", "Sofie", "Tom"]
    last = ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems", "Claes", "Goossens", "Wouters",
            "De Smet", "Van den Berg", "El Amrani", "Dubois", "Lambert", "Martin"]
    n = 240
    people = [(first[rng.integers(len(first))], last[rng.integers(len(last))]) for _ in range(n)]
    nums = rng.integers(400_000_000, 499_999_999, size=n)
    plans = rng.choice(["basic", "plus", "prepaid", "business"], size=n)
    days = pd.Timestamp("2022-01-01") + pd.to_timedelta(rng.integers(0, 1400, size=n), unit="D")
    bal = np.round(rng.uniform(-20, 400, size=n), 2)

    def name(f, l, k):
        return [f"{f} {l}", f"  {f.lower()} {l.upper()}", f"{f}  {l} ", f"{l}, {f}"][k]

    def phone(d, k):
        s = str(d)
        return [f"0{s[:3]} {s[3:5]} {s[5:7]} {s[7:]}", f"+32 {s[:3]} {s[3:5]} {s[5:7]} {s[7:]}",
                f"0032{s}", f"0{s}", s][k]

    def date(d, k):
        return [d.strftime("%Y-%m-%d"), d.strftime("%d/%m/%Y"), d.strftime("%B %d, %Y"), d.strftime("%d-%b-%y")][k]

    def money(b, k):
        return [f"{b:.2f}", f"€ {b:,.2f}", f"{b:.2f} EUR", "N/A", "-", ""][k]

    rows = []
    for i in range(n):
        rows.append({
            "name": name(*people[i], rng.integers(0, 4)),
            "phone": phone(nums[i], rng.integers(0, 5)),
            "plan": [plans[i], plans[i].title(), plans[i].upper(), plans[i] + " "][rng.integers(0, 4)],
            "signup": date(days[i], rng.integers(0, 4)),
            "balance": money(bal[i], rng.choice(6, p=[0.45, 0.2, 0.15, 0.08, 0.07, 0.05])),
        })
    df = pd.DataFrame(rows)
    # 25 contacts appear twice, written in another format.
    dup_ix = rng.choice(n, size=25, replace=False)
    again = []
    for i in dup_ix:
        r = dict(rows[i])
        r["name"] = name(*people[i], (rng.integers(1, 4)))
        r["phone"] = phone(nums[i], rng.integers(0, 5))
        again.append(r)
    # Six rows that no cleaning rule can repair. A cleaner must report them, not guess.
    broken = pd.DataFrame([
        {"name": "Test Account", "phone": "12 34", "plan": "basic", "signup": "2024-02-01", "balance": "10.00"},
        {"name": "Visitor UK", "phone": "+44 7700 900123", "plan": "plus", "signup": "2024-03-02", "balance": "5.00"},
        {"name": "Gold Member", "phone": "0477 11 22 33", "plan": "gold", "signup": "2024-04-03", "balance": "7.50"},
        {"name": "Leap Day", "phone": "0477 44 55 66", "plan": "basic", "signup": "31/02/2024", "balance": "1.00"},
        {"name": "Someday Soon", "phone": "0477 77 88 99", "plan": "plus", "signup": "someday", "balance": "2.00"},
        {"name": "Words Only", "phone": "0478 12 12 12", "plan": "prepaid", "signup": "2024-05-04", "balance": "twelve euros"},
    ])
    return (pd.concat([df, pd.DataFrame(again), broken], ignore_index=True)
            .sample(frac=1, random_state=7).reset_index(drop=True))


def traces(call_table: pd.DataFrame) -> list[dict]:
    rng = _rng(6)
    sample = call_table.sample(500, random_state=11).reset_index(drop=True)
    out = []
    for r in sample.itertuples():
        ev = [{"t_ms": 0, "type": "INVITE"}]
        t = 0
        if r.status == "failed":
            t += int(rng.integers(30, 300))
            ev.append({"t_ms": t, "type": "RESPONSE", "code": 503})
        elif r.status == "busy":
            t += int(rng.integers(80, 400))
            ev += [{"t_ms": t, "type": "RESPONSE", "code": 100}]
            t += int(rng.integers(50, 200))
            ev.append({"t_ms": t, "type": "RESPONSE", "code": 486})
        else:
            for code in (100, 180):
                t += int(rng.integers(40, 900))
                ev.append({"t_ms": t, "type": "RESPONSE", "code": code})
            if r.status == "answered":
                t += int(rng.integers(500, 9000))
                ev += [{"t_ms": t, "type": "RESPONSE", "code": 200}, {"t_ms": t + 20, "type": "ACK"}]
                ev.append({"t_ms": t + int(r.duration_s) * 1000, "type": "BYE"})
            else:
                t += 30_000
                ev.append({"t_ms": t, "type": "RESPONSE", "code": 408})
        rec = {"call_id": int(r.call_id), "caller": r.caller, "events": ev,
               "meta": {"cell": r.cell_id if isinstance(r.cell_id, str) else None,
                        "codec": r.codec if isinstance(r.codec, str) else None,
                        "roaming": bool(r.roaming)}}
        if rng.random() < 0.04:
            del rec["meta"]
        if rng.random() < 0.02:
            rec["events"] = []
        out.append(rec)
    return out


def runs() -> list[dict]:
    """Results of an evaluation: 150 tasks x 2 configurations x 3 seeds."""
    rng = _rng(7)
    cats = ["billing", "routing", "roaming", "outage", "device"]
    out = []
    for k in range(150):
        cat = cats[k % 5]
        hard = rng.beta(2, 2)
        for config, boost in (("baseline", 0.0), ("improved", 0.07)):
            p = float(np.clip(0.92 - 0.7 * hard + boost, 0.02, 0.98))
            for seed in range(3):
                prompt = int(rng.integers(300, 1500))
                out.append({"task_id": f"t{k + 1:03d}", "category": cat, "config": config, "seed": seed,
                            "passed": bool(rng.random() < p),
                            "latency_ms": int(rng.lognormal(np.log(1200 + 600 * hard), 0.3)),
                            "tokens": {"prompt": prompt, "completion": int(rng.integers(20, 400))}})
    return out


def build(out: pathlib.Path = DATA) -> None:
    out.mkdir(exist_ok=True)
    cell_table, subs = cells(), subscribers()
    cell_table.to_csv(out / "cells.csv", index=False)
    subs.to_csv(out / "subscribers.csv", index=False)
    PLANS.to_csv(out / "plans.csv", index=False)
    call_table = calls(subs, cell_table)
    call_table.to_csv(out / "calls.csv", index=False)
    kpi(cell_table).to_csv(out / "kpi.csv", index=False)
    messy_contacts().to_csv(out / "contacts_messy.csv", index=False)
    with open(out / "traces.jsonl", "w", encoding="utf-8") as f:
        for rec in traces(call_table):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(out / "runs.jsonl", "w", encoding="utf-8") as f:
        for rec in runs():
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    build()
    for p in sorted(DATA.iterdir()):
        print(f"{p.name:20s} {p.stat().st_size:>9,d} bytes")
