"""WireGuard backend: profile discovery, status, connect/disconnect.

All privileged operations go through app.backend.privilege. This module
never calls subprocess directly for elevated work.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path

from app.backend import privilege
from app.config import settings
from app.utils.logging_setup import safe_log

DEFAULT_WG_DIR = "/etc/wireguard"
HANDSHAKE_TIMEOUT = 180
VALID_PROFILE_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
ALLOWED_ACTIONS = ("up", "down")
OP_TIMEOUT = 30


# ---------------------------------------------------------------- unprivileged discovery
def list_profiles(target_dir: str | Path = DEFAULT_WG_DIR) -> list[str]:
    """Best-effort unprivileged listing. Returns [] if the directory is
    unreadable. Provided for tests; the GUI uses list_profiles_privileged."""
    profiles: list[str] = []
    target_path = Path(target_dir)
    if not target_path.is_dir():
        safe_log(f"WireGuard directory not found: {target_path}", logging.WARNING)
        return profiles
    try:
        entries = list(target_path.iterdir())
    except PermissionError:
        safe_log(f"Permission denied listing {target_path}", logging.WARNING)
        return profiles
    for entry in entries:
        if not entry.is_file() or entry.suffix != ".conf":
            continue
        try:
            has_interface = has_peer = False
            with entry.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped == "[Interface]":
                        has_interface = True
                    elif stripped == "[Peer]":
                        has_peer = True
            if has_interface and has_peer:
                profiles.append(entry.stem)
            else:
                safe_log(f"Skipping {entry.name}: missing sections", logging.WARNING)
        except PermissionError:
            safe_log(f"Permission denied reading {entry.name}", logging.WARNING)
        except Exception as e:
            safe_log(f"Error reading {entry.name}: {e}", logging.ERROR)
    return sorted(profiles)


# ---------------------------------------------------------------- privileged discovery
def list_profiles_privileged() -> dict:
    """Run the privileged helper and parse its JSON. Blocks up to OP_TIMEOUT.

    Returns:
        {"ok": True,  "profiles": [str, ...]}
        {"ok": False, "error": "<code>", "detail": "<human text>"}
    """
    try:
        proc = privilege.run_helper(timeout=OP_TIMEOUT)
    except FileNotFoundError as e:
        return {"ok": False, "error": "helper_missing", "detail": str(e)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "detail": "Helper timed out"}
    except Exception as e:
        return {"ok": False, "error": "spawn_failed", "detail": str(e)}

    if proc.returncode == 126:
        return {"ok": False, "error": "auth_cancelled",
                "detail": (proc.stderr or "Authentication cancelled").strip()}
    if proc.returncode != 0:
        # Try to read helper's structured error if present.
        try:
            parsed = json.loads(proc.stdout.strip())
            if isinstance(parsed, dict) and parsed.get("ok") is False:
                return {"ok": False,
                        "error": parsed.get("error", "helper_failed"),
                        "detail": (proc.stderr or "").strip()}
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"ok": False, "error": "helper_failed",
                "detail": (proc.stderr or proc.stdout or "").strip() or "no output"}

    try:
        parsed = json.loads(proc.stdout.strip())
        if parsed.get("ok") is True and isinstance(parsed.get("profiles"), list):
            return {"ok": True, "profiles": parsed["profiles"]}
        return {"ok": False, "error": "bad_helper_output",
                "detail": proc.stdout.strip()[:200]}
    except (json.JSONDecodeError, AttributeError) as e:
        return {"ok": False, "error": "bad_helper_output", "detail": str(e)}


# ---------------------------------------------------------------- status
def get_status() -> dict:
    """Read-only kernel status."""
    result = {"state": "disconnected", "interface": None, "detail": ""}
    
    try:
        # 1. Check for WireGuard interfaces using 'ip link' (no root required)
        ip_proc = subprocess.run(
            ["/usr/sbin/ip", "link", "show"],
            capture_output=True, text=True, timeout=5, check=False
        )
        
        # Look for lines like "5: proton: <POINTOPOINT,NOARP,UP,LOWER_UP>"
        wg_iface = None
        for line in ip_proc.stdout.splitlines():
            if "wireguard" in line.lower() or ": proton:" in line or ": wg" in line:
                # Extract the name between the first set of colons
                parts = line.split(":")
                if len(parts) >= 2:
                    candidate = parts[1].strip()
                    # Simple heuristic: our VPN interfaces usually have no dots
                    if "." not in candidate:
                        wg_iface = candidate
                        break
        
        if not wg_iface:
            return result  # Truly disconnected
            
        result["interface"] = wg_iface
        result["state"] = "connected"  # If the interface exists, assume it's up

        # 2. Try to get handshake data (needs root)
        hs = subprocess.run(
            [settings.WG_PATH, "show", wg_iface, "latest-handshakes"],
            capture_output=True, text=True, timeout=5, check=False
        )
        
        if hs.returncode != 0:
            # We are connected but can't read details
            result["detail"] = "Connected (unprivileged status)"
            return result

        # Parse handshakes to see if it's truly active
        now = time.time()
        active = False
        for line in hs.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    if 0 < int(parts[1]) and (now - int(parts[1])) < HANDSHAKE_TIMEOUT:
                        active = True
                        break
                except ValueError:
                    pass
                    
        if active:
            result["state"] = "connected"
            result["detail"] = ""
        else:
            result["state"] = "disconnected"
            result["detail"] = "Interface up, no recent handshake"
            
    except Exception as e:
        result["state"] = "error"
        result["detail"] = f"Unexpected error: {e}"
        
    return result


def _run_privileged_wg(action: str, profile: str) -> dict:
    if action not in ALLOWED_ACTIONS:
        return {"success": False, "code": -1, "message": "Invalid action."}
    if not VALID_PROFILE_RE.match(profile):
        return {"success": False, "code": -1, "message": "Invalid profile name."}
    try:
        proc = privilege.run_privileged(
            [settings.WG_QUICK_PATH, action, profile], timeout=OP_TIMEOUT
        )
    except FileNotFoundError as e:
        return {"success": False, "code": -1, "message": str(e)}
    except PermissionError as e:
        return {"success": False, "code": -1, "message": str(e)}
    except subprocess.TimeoutExpired:
        return {"success": False, "code": -2, "message": "Operation timed out."}
    except Exception as e:
        return {"success": False, "code": -3, "message": str(e)}

    if proc.returncode == 0:
        return {"success": True, "code": 0, "message": "Success"}
    detail = (proc.stderr or proc.stdout or "").strip() or "Unknown error"
    if proc.returncode == 126:
        return {"success": False, "code": 126,
                "message": f"Authentication cancelled/failed. {detail}"}
    if proc.returncode == 127:
        return {"success": False, "code": 127,
                "message": f"Command failed to execute. {detail}"}
    return {"success": False, "code": proc.returncode, "message": detail}


def connect(profile: str) -> dict:
    return _run_privileged_wg("up", profile)


def disconnect(profile: str) -> dict:
    return _run_privileged_wg("down", profile)


def wait_for_state(expected_state: str, expected_interface: str | None,
                   timeout: float = 4.0, interval: float = 0.25) -> dict:
    """Poll kernel state until it matches or timeout expires. Caller is a
    worker thread (not the GUI thread)."""
    deadline = time.monotonic() + timeout
    last = {"state": "unknown", "interface": None, "detail": ""}
    while time.monotonic() < deadline:
        last = get_status()
        if last["state"] == expected_state:
            if expected_state == "connected" and expected_interface:
                if last.get("interface") == expected_interface:
                    return last
            elif expected_state == "disconnected":
                return last
        time.sleep(interval)
    return last
