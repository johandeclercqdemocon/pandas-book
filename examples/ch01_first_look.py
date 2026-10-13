"""Chapter 1: a first look at the call records."""
import pandas as pd

from pdbook.looks import first_look, headline

calls = pd.read_csv("data/calls.csv")
print(headline(calls))
print(first_look(calls))
