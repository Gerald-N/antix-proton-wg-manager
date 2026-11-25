"""Centralised settings for the Proton VPN WireGuard Manager.

PRIVILEGE_RUNNER selects how elevated commands are launched:
    "sudo"    - development (terminal password prompt)
    "pkexec"  - production (graphical Polkit authentication)

The Assignment 15 .deb package will ship this file with PRIVILEGE_RUNNER
set to "pkexec".
"""
from __future__ import annotations

import os
from pathlib import Path

# --- privilege runner ------------------------------------------------
PRIVILEGE_RUNNER = "sudo"

# --- absolute executable paths --------------------------------------
SUDO_PATH       = "/usr/bin/sudo"
PKEXEC_PATH     = "/usr/bin/pkexec"
WG_PATH         = "/usr/bin/wg"
WG_QUICK_PATH   = "/usr/bin/wg-quick"
PYTHON_PATH     = "/usr/bin/python3"

# --- privileged helper ----------------------------------------------
# Only this script may be executed via PYTHON_PATH through the
# privilege layer. The path is resolved relative to this package.
HELPER_PATH = str(
    (Path(__file__).resolve().parent.parent / "backend" / "wg_list_profiles.py")
)
# Production alternative (installed by Assignment 15). If present, it
# takes precedence over the development copy.
HELPER_PATH_PRODUCTION = "/usr/libexec/proton-wg-manager/wg_list_profiles.py"


def effective_helper_path() -> str:
    """Return the helper path to use, preferring the installed copy."""
    if os.path.isfile(HELPER_PATH_PRODUCTION):
        return HELPER_PATH_PRODUCTION
    return HELPER_PATH
