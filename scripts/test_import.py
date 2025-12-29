#!/usr/bin/env python3
"""Minimal test to diagnose import failure from Liquidsoap context."""
import os
import sys
from pathlib import Path

# Write to a file immediately, bypassing any buffering
test_log = Path("/tmp/ai_radio_logs/import_test.log")
with open(test_log, "a") as f:
    f.write(f"=== Test started: {sys.argv} ===\n")
    f.write(f"CWD: {os.getcwd()}\n")
    f.write(f"USER: {os.environ.get('USER', 'NOT SET')}\n")
    f.write(f"HOME: {os.environ.get('HOME', 'NOT SET')}\n")
    f.write(f"PATH: {os.environ.get('PATH', 'NOT SET')[:100]}...\n")
    f.write(f".env exists in CWD: {Path('.env').exists()}\n")
    f.write(f".env exists in /srv/ai_radio: {Path('/srv/ai_radio/.env').exists()}\n")
    f.flush()

    try:
        f.write("1. Adding src to path...\n")
        f.flush()
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        f.write(f"   sys.path: {sys.path[:3]}\n")
        f.flush()

        f.write("2. Importing config...\n")
        f.flush()
        from ai_radio.config import config
        f.write("   SUCCESS!\n")
        f.write(f"   config.paths.db_path: {config.paths.db_path}\n")
        f.flush()

    except Exception as e:
        f.write(f"   FAILED: {type(e).__name__}: {e}\n")
        import traceback
        f.write(traceback.format_exc())
        f.flush()
        sys.exit(1)

print("Test passed - check /tmp/ai_radio_logs/import_test.log")
