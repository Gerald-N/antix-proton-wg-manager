"""Centralised privileged command execution."""
from __future__ import annotations

import os
import subprocess
from app.config import settings

_RUNNER = settings.SUDO_PATH
if settings.PRIVILEGE_RUNNER == "pkexec":
    _RUNNER = settings.PKEXEC_PATH

def _verify_executable(path: str, *, what: str) -> None:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        raise FileNotFoundError(f"{what} missing or non-executable: {path}")

def _allowed_argv(argv: list[str]) -> bool:
    if not argv: return False
    # connect / disconnect
    if len(argv) == 3 and argv[0] == settings.WG_QUICK_PATH and argv[1] in ("up", "down"): return True
    # profile loading helper
    if len(argv) == 2 and argv[0] == settings.PYTHON_PATH and argv[1] == settings.effective_helper_path(): return True
    # get_status: wg show interfaces
    if len(argv) == 3 and argv[0] == settings.WG_PATH and argv[1] == "show" and argv[2] == "interfaces": return True
    # get_status: wg show <iface> latest-handshakes
    if len(argv) == 4 and argv[0] == settings.WG_PATH and argv[1] == "show" and argv[3] == "latest-handshakes": return True
    # wifi: nmcli
    if argv[0] == "/usr/bin/nmcli": return True
    return False

def run_privileged(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    if not isinstance(argv, list) or not argv: raise ValueError("argv must be non-empty")
    if not _allowed_argv(argv): raise PermissionError(f"Not in allowlist: {argv!r}")
    _verify_executable(_RUNNER, what="privilege runner")
    _verify_executable(argv[0], what="target executable")

    env = os.environ.copy()
    env["SUDO_ASKPASS"] = "/usr/bin/ssh-askpass"

    if _RUNNER.endswith("sudo"):
        cmd = [_RUNNER, "-A", "--"] + argv
    else:
        cmd = [_RUNNER, "--"] + argv

    return subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        timeout=timeout, 
        check=False,
        stdin=subprocess.DEVNULL,
        env=env
    )

def run_helper(timeout: int = 30) -> subprocess.CompletedProcess:
    _verify_executable(settings.PYTHON_PATH, what="python3")
    helper = settings.effective_helper_path()
    _verify_executable(helper, what="helper")
    return run_privileged([settings.PYTHON_PATH, helper], timeout=timeout)
