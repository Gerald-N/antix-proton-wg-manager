#!/usr/bin/python3
"""Privileged helper: list /etc/wireguard/*.conf stem names.

Contract:
  * Reads ONLY directory metadata via os.scandir.
  * NEVER opens a .conf file.
  * Does not follow symlinks.
  * Accepts no CLI arguments.
  * Emits exactly one line of JSON to stdout.
  * Exits 0 on success, 1 on any error.
"""
from __future__ import annotations

import json
import os
import re
import sys

WGDIR = "/etc/wireguard"
VALID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def emit(obj: dict, code: int) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()
    sys.exit(code)


def main() -> None:
    if len(sys.argv) > 1:
        emit({"ok": False, "error": "arguments_not_accepted"}, 1)

    try:
        entries = list(os.scandir(WGDIR))
    except FileNotFoundError:
        emit({"ok": False, "error": "directory_missing"}, 1)
    except PermissionError:
        emit({"ok": False, "error": "directory_unreadable"}, 1)
    except OSError as e:
        emit({"ok": False, "error": f"os_error:{e.errno}"}, 1)

    profiles = []
    for entry in entries:
        try:
            if entry.is_symlink():
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
        except OSError:
            continue
        name = entry.name
        if not name.endswith(".conf"):
            continue
        stem = name[:-5]
        if not VALID_RE.match(stem):
            continue
        profiles.append(stem)

    emit({"ok": True, "profiles": sorted(profiles)}, 0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never leak a traceback through pkexec
        emit({"ok": False, "error": f"unhandled:{type(e).__name__}"}, 1)
