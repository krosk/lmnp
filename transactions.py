"""
Fetch BNP Paribas transactions and write them to a CSV file.
Usage: python transactions.py [output.csv]
"""
import csv
import sys
from woob.core import Woob

ACCOUNT_ID = "2741588268268091098854133206841022789888175395311928935481"
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "transactions.csv"

w = Woob()
backends = list(w.load_backends(modules=["bnp"]).values())
backend = backends[0]

account = next(a for a in backend.iter_accounts() if a.id.startswith(ACCOUNT_ID))

rows = []
for tr in backend.iter_history(account):
    rows.append({
        "date": tr.date.strftime("%Y-%m-%d"),
        "label": tr.label,
        "amount": tr.amount,
    })

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "label", "amount"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} transactions to {OUTPUT}")
