"""Clean the messy contact export, and say what could not be cleaned."""
from __future__ import annotations

import re

import pandas as pd

_E164_BE = re.compile(r"^\+32\d{9}$")
_MISSING_MONEY = {"", "-", "n/a", "na", "null"}
PLANS = ("prepaid", "basic", "plus", "business")


def e164(phone: pd.Series) -> pd.Series:
    """Belgian numbers to +32xxxxxxxxx. Anything that does not fit becomes NaN."""
    digits = phone.str.replace(r"[^\d+]", "", regex=True)      # drop spaces, dots, dashes
    digits = digits.str.replace(r"^\+", "00", regex=True)       # +32 -> 0032
    national = digits.str.replace(r"^0032", "", regex=True)     # 0032477... -> 477...
    national = national.str.replace(r"^0", "", regex=True)      # 0477... -> 477...
    out = "+32" + national
    return out.where(out.str.match(_E164_BE) & national.str.len().eq(9))


def name_key(name: pd.Series) -> pd.Series:
    """A key for comparing names: trimmed, one space, case-folded, 'Last, First' turned round."""
    n = name.str.strip().str.replace(r"\s+", " ", regex=True)
    flipped = n.str.replace(r"^(.+?),\s*(.+)$", r"\2 \1", regex=True)
    return flipped.str.casefold()


def money(s: pd.Series) -> pd.Series:
    """'€ 1,234.50', '12.5 EUR', '-3.64' -> float. '-', 'N/A' and '' -> NaN."""
    raw = s.str.strip()
    missing = raw.str.lower().isin(_MISSING_MONEY) | raw.isna()
    num = raw.str.replace(r"[€\s]|EUR$", "", regex=True).str.replace(",", "", regex=False)
    return pd.to_numeric(num.where(~missing), errors="coerce")


DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d-%b-%y")


def dates(s: pd.Series) -> pd.Series:
    """The four date formats of the export, each read with its exact format. Anything else becomes NaT.

    One exact format for each pattern, and not `format="mixed", dayfirst=True`: with `dayfirst=True` the
    mixed parser also swaps day and month in an ISO date such as 2024-11-04.
    """
    text = s.str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[us]")
    for fmt in DATE_FORMATS:
        out = out.fillna(pd.to_datetime(text, format=fmt, errors="coerce").astype("datetime64[us]"))
    return out


def clean_contacts(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, rejects). `rejects` lists each value that could not be parsed."""
    df = pd.DataFrame(index=raw.index)
    df["name"] = raw["name"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["name_key"] = name_key(raw["name"])
    df["phone"] = e164(raw["phone"])
    df["plan"] = raw["plan"].str.strip().str.lower()
    df["signup"] = dates(raw["signup"])
    df["balance"] = money(raw["balance"])

    money_marker = raw["balance"].str.strip().str.lower().isin(_MISSING_MONEY) | raw["balance"].isna()
    bad = {
        "phone": df["phone"].isna() & raw["phone"].notna(),
        "plan": ~df["plan"].isin(PLANS),
        "signup": df["signup"].isna() & raw["signup"].notna(),
        "balance": df["balance"].isna() & ~money_marker,
    }
    rejects = pd.concat(
        [pd.DataFrame({"row": raw.index[m], "column": col, "raw": raw.loc[m, col].to_numpy()})
         for col, m in bad.items() if m.any()],
        ignore_index=True,
    ) if any(m.any() for m in bad.values()) else pd.DataFrame(columns=["row", "column", "raw"])
    df["plan"] = df["plan"].where(df["plan"].isin(PLANS))
    # duplicated() treats two missing phones as equal. A missing key is not a duplicate.
    repeat = df.duplicated(subset="phone", keep="first") & df["phone"].notna()
    clean = df[~repeat].reset_index(drop=True)
    return clean, rejects
