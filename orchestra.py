#!/usr/bin/env python
"""orchestra.py — Download documents from the Orchestra/Egiweb copropriété portal.

Portal:      https://www.orchestrav2.egiweb.net/
Credentials: ORCHESTRA_LOGIN and ORCHESTRA_PASSWORD in .claude/.env

Usage:
  python orchestra.py [output_dir]           # download appels de fonds (default: charges/)
  python orchestra.py --type all [output_dir] # download all document types
  python orchestra.py --list                  # list available documents without downloading

Document types available:
  @FGC  appel de fonds (default)
  @XCC  annexe de répartition
  @CCC  compte copropriétaire
  @JCC  journal de charges
  @DCC  détail de charges
  @D04  correspondance / autres documents
"""
import os
import re
import sys
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings()

BASE = "https://www.orchestrav2.egiweb.net"

DOC_TYPES = {
    "@FGC": "appel_fonds",
    "@XCC": "annexe_repartition",
    "@CCC": "compte_coproprietaire",
    "@JCC": "journal_charges",
    "@DCC": "detail_charges",
    "@D04": "courrier",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_env():
    env_path = Path(".claude/.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def make_session():
    s = requests.Session()
    s.verify = False
    return s


def login(session):
    login_val = os.environ.get("ORCHESTRA_LOGIN")
    password_val = os.environ.get("ORCHESTRA_PASSWORD")
    if not login_val or not password_val:
        raise SystemExit(
            "Error: ORCHESTRA_LOGIN and ORCHESTRA_PASSWORD must be set "
            "(add them to .claude/.env)"
        )
    session.post(f"{BASE}/admin/pwd.php", data={
        "login": login_val,
        "password": password_val,
        "url_param": "",
        "comment": "",
        "Submit": "Connexion",
    })
    session.get(f"{BASE}/admin/login-2.php")


def list_documents(session):
    """Return list of (hex_str, decoded_name, label) for all documents on Docnew.php."""
    r = session.get(f"{BASE}/Works/Docnew.php")
    entries = re.findall(
        r'onClick="javascript:send\(\'([0-9a-fA-F]+)\'\)">([^<]+)</a>',
        r.text,
    )
    docs = []
    for hex_str, label in entries:
        decoded = bytes.fromhex(hex_str).decode("ascii", errors="replace")
        docs.append((hex_str, decoded, label.strip()))
    return docs


def download_document(session, hex_str):
    """POST to document.php with the hex-encoded filename. Returns PDF bytes."""
    r = session.post(f"{BASE}/Works/document.php", data={"DocName": hex_str})
    ct = r.headers.get("Content-Type", "")
    if r.status_code != 200 or "pdf" not in ct.lower():
        raise RuntimeError(
            f"Download failed: status={r.status_code}, Content-Type={ct}"
        )
    return r.content


def decoded_to_filename(decoded):
    """
    Map a decoded document name to a human-readable filename.
    '@FGC0217_00039_20250401_20250401.PDF' -> 'appel_fonds_20250401.pdf'
    '@XCC0217_00039_20240101_20250331.PDF' -> 'annexe_repartition_20240101_20250331.pdf'
    '@D04230249575.PDF'                    -> 'courrier_D04230249575.pdf'
    """
    for prefix, type_name in DOC_TYPES.items():
        if decoded.startswith(prefix):
            dates = re.findall(r"_(\d{8})", decoded)
            if dates:
                return f"{type_name}_{'_'.join(dates)}.pdf"
            # fallback: use the raw ID part
            raw = decoded.lstrip("@").rstrip(".PDF").rstrip(".pdf")
            return f"{type_name}_{raw}.pdf"
    # unknown prefix
    safe = re.sub(r"[^\w.-]", "_", decoded.lstrip("@"))
    return safe.lower()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    load_env()

    output_dir = Path("charges")
    list_only = False
    filter_prefixes = {"@FGC"}

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--list":
            list_only = True
        elif arg == "--type":
            i += 1
            if i < len(args):
                t = args[i].strip()
                if t.lower() == "all":
                    filter_prefixes = set(DOC_TYPES.keys())
                else:
                    filter_prefixes = {p.upper() if not p.startswith("@") else p
                                       for p in t.split(",")}
        elif not arg.startswith("-"):
            output_dir = Path(arg)
        i += 1

    session = make_session()

    print("Logging in to Orchestra...")
    login(session)

    print("Fetching document list...")
    docs = list_documents(session)

    filtered = [
        (h, d, l) for h, d, l in docs
        if any(d.startswith(p) for p in filter_prefixes)
    ]

    if list_only:
        print(f"\n{'Decoded name':50s}  Label")
        print("-" * 90)
        for _, decoded, label in filtered:
            print(f"  {decoded:50s}  {label}")
        print(f"\n{len(filtered)} document(s) found.")
        return

    output_dir.mkdir(exist_ok=True)

    new_count = 0
    errors = []
    for hex_str, decoded, label in filtered:
        filename = decoded_to_filename(decoded)
        out_path = output_dir / filename
        if out_path.exists():
            print(f"  skip (exists): {filename}")
            continue
        print(f"  downloading:   {label}  ->  {filename}")
        try:
            pdf_bytes = download_document(session, hex_str)
            out_path.write_bytes(pdf_bytes)
            new_count += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            errors.append((filename, str(e)))

    print(f"\n{new_count} new file(s) saved to {output_dir}/")
    if errors:
        print(f"{len(errors)} error(s):")
        for fname, err in errors:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
