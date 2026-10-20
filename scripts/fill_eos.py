"""Compatibility entry point for the reviewed lifecycle audit (dry-run by default).

Use --apply to back up and correct legacy automatic fields using application DB configuration.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.scripts.audit_asset_eos import main

if __name__ == '__main__':
    main()
