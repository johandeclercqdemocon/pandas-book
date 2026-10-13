"""Chapter 6: clean the contact export and list what could not be cleaned."""
import pandas as pd

from pdbook.clean import clean_contacts

raw = pd.read_csv("data/contacts_messy.csv", dtype=str)
clean, rejects = clean_contacts(raw)
print(f"raw rows     : {len(raw)}")
print(f"clean rows   : {len(clean)}")
print(f"duplicates   : {len(raw) - len(clean)}")
print(f"rejected     : {len(rejects)} value(s)")
print(rejects.to_string(index=False))
