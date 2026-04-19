"""
Re-apply local patches to the woob bnp module after a fresh install or woob update.

Usage: python apply_patches.py [--dry-run]
"""
import shutil
import sys
from pathlib import Path
from woob.core import Woob

DRY_RUN = "--dry-run" in sys.argv

WOOB_MODULES = Path(Woob().repositories.modules_dir) / "bnp" / "pp"
PATCHES = Path(__file__).parent / "patches" / "bnp" / "pp"

FILES = ["pages.py", "browser.py", "document_pages.py"]

if not WOOB_MODULES.exists():
    print(f"ERROR: woob bnp module not found at {WOOB_MODULES}")
    print("Run: python -m woob config install bnp")
    sys.exit(1)

for name in FILES:
    src = PATCHES / name
    dst = WOOB_MODULES / name
    if DRY_RUN:
        print(f"[dry-run] {src} -> {dst}")
    else:
        shutil.copy2(src, dst)
        print(f"Patched {dst}")

if not DRY_RUN:
    print("Done. Patches applied.")
