"""
Convert BNP Paribas PDF statements to CSV using the Claude API.
Usage: python bnp_pdf_to_csv.py [output.csv]

Appends new transactions to a master CSV (default: statements.csv). Only
*_4225_*.pdf files (joint account statements) are processed; *_8946_*.pdf
mortgage documents are ignored. PDFs with an existing .pdf_cache/ entry are
skipped — subsequent runs only process and append newly added files.

PDFs are sent as base64-encoded document blocks (no Files API) so this works
with Vertex AI and other non-Anthropic-native endpoints.
"""
import base64
import csv
import json
import os
import re
import sys
from pathlib import Path

import anthropic

STATEMENTS_DIR = Path(__file__).parent / "statements"
CACHE_DIR = Path(__file__).parent / ".pdf_cache"
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "statements.csv"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6--111582")

PROMPT = """Extract all transactions from this BNP Paribas bank statement.

Return ONLY a JSON array with one object per transaction, using these exact fields:
- "date": string in YYYY-MM-DD format
- "label": string, the transaction description as printed
- "amount": number, negative for debits, positive for credits

Example:
[
  {"date": "2024-01-27", "label": "VIREMENT RECU CLIENT", "amount": 2300.00},
  {"date": "2024-01-10", "label": "CARTE 10/01 MONOPRIX PARIS", "amount": -45.30}
]

Do not include the opening balance, closing balance, or any non-transaction lines.
Output nothing except the JSON array."""


def extract_transactions(client: anthropic.Anthropic, pdf_path: Path) -> list[dict]:
    cache_file = CACHE_DIR / (pdf_path.stem + ".json")
    if cache_file.exists():
        print(f"  (cached)")
        return json.loads(cache_file.read_text(encoding="utf-8"))

    print(f"extracting...", end=" ", flush=True)
    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": PROMPT},
            ],
        }],
    )

    text = response.content[0].text.strip()

    # Strip markdown fences if Claude wrapped the JSON
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Find the JSON array in case there's surrounding prose
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        text = match.group(0)

    transactions = json.loads(text)

    CACHE_DIR.mkdir(exist_ok=True)
    cache_file.write_text(
        json.dumps(transactions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return transactions


def main():
    pdfs = sorted(STATEMENTS_DIR.glob("*_4225_*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {STATEMENTS_DIR}")
        sys.exit(1)

    new_pdfs = [p for p in pdfs if not (CACHE_DIR / (p.stem + ".json")).exists()]
    if not new_pdfs:
        print(f"No new PDFs to process ({len(pdfs)} already cached).")
        return

    print(f"Processing {len(new_pdfs)} new PDF(s) of {len(pdfs)} total...")
    client = anthropic.Anthropic()
    new_rows = []
    errors = []

    for pdf in new_pdfs:
        print(f"{pdf.name}:", end=" ", flush=True)
        try:
            transactions = extract_transactions(client, pdf)
            new_rows.extend(transactions)
            print(f"{len(transactions)} transactions")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append((pdf.name, str(e)))

    if new_rows:
        new_rows.sort(key=lambda r: r["date"])
        master_exists = Path(OUTPUT).exists()
        with open(OUTPUT, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "label", "amount"])
            if not master_exists:
                writer.writeheader()
            writer.writerows(new_rows)
        print(f"\nAppended {len(new_rows)} transactions to {OUTPUT}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for name, err in errors:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
