"""Wi-Fi backend using NetworkManager (nmcli)."""
from __future__ import annotations

import subprocess
import logging
from app.utils.logging_setup import safe_log
from app.backend import privilege

NMCLI_PATH = "/usr/bin/nmcli"

def _run(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [NMCLI_PATH] + args,
            capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "nmcli not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "Command timed out")

def get_current_wifi() -> dict:
    proc = _run(["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status"])
    if proc.returncode != 0:
        return {"connected": False, "ssid": None}

    for line in proc.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 4 and parts[1] == "wifi":
            device, _, state, connection = parts[:4]
            if state == "connected":
                # Fetch signal strength
                signal = 100
                sig_proc = _run(["-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list"])
                for line in sig_proc.stdout.strip().splitlines():
                    p = line.split(":")
                    if len(p) >= 2 and p[0] == "*":
                        try:
                            signal = int(p[1])
                        except ValueError:
                            pass
                        break
                return {"connected": True, "ssid": connection, "device": device, "signal": signal}
            else:
                return {"connected": False, "ssid": None, "device": device, "signal": 0}

    return {"connected": False, "ssid": None, "signal": 0}

def get_saved_connections() -> list[str]:
    """Returns a list of saved connection names (SSIDs)."""
    proc = _run(["-t", "-f", "NAME,TYPE", "connection", "show"])
    if proc.returncode != 0:
        return []
    saved = []
    for line in proc.stdout.strip().splitlines():
        if ":" not in line:
            continue
        name, ctype = line.rsplit(":", 1)
        name = name.replace("\\:", ":")
        # NetworkManager reports type as '802-11-wireless' for Wi-Fi
        if ctype.strip() in ("wifi", "802-11-wireless"):
            saved.append(name.strip())
    return saved

def scan_networks() -> list[dict]:
    _run(["--rescan", "yes", "device", "wifi", "list"])
    proc = _run(["-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
    if proc.returncode != 0:
        return []

    networks = []
    seen = set()
    for line in proc.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 3:
            ssid = parts[0].strip()
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            try:
                signal = int(parts[1])
            except ValueError:
                signal = 0
            security = parts[2] if parts[2] else "Open"
            networks.append({"ssid": ssid, "signal": signal, "security": security})

    networks.sort(key=lambda x: x["signal"], reverse=True)
    return networks

def connect_wifi(ssid: str, password: str | None = None) -> dict:
    """Connects to a Wi-Fi network using the privilege runner."""
    if password:
        # New network: connect with password
        args = [NMCLI_PATH, "device", "wifi", "connect", ssid, "password", password]
    else:
        # Saved network: bring up by name
        args = [NMCLI_PATH, "connection", "up", "id", ssid]

    try:
        # We pass the whole command list to the privilege runner
        proc = privilege.run_privileged(args, timeout=30)
    except Exception as e:
        return {"success": False, "message": str(e)}

    if proc.returncode == 0:
        return {"success": True, "message": "Connected"}
    
    err = (proc.stderr or proc.stdout or "").strip()
    if "Insufficient privileges" in err or "not authorized" in err.lower():
        err = "Authentication failed or cancelled."
    return {"success": False, "message": err or "Unknown error"}

def disconnect_wifi() -> dict:
    """Disconnects the current Wi-Fi device."""
    # Find the wifi device
    proc = _run(["-t", "-f", "DEVICE,TYPE", "device", "status"])
    device = None
    if proc.returncode == 0:
        for line in proc.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == "wifi":
                device = parts[0]
                break

    if not device:
        return {"success": False, "message": "No Wi-Fi device found"}

    # Disconnect it (requires privilege via nmcli)
    args = [NMCLI_PATH, "device", "disconnect", device]
    
    try:
        proc = privilege.run_privileged(args, timeout=15)
    except Exception as e:
        return {"success": False, "message": str(e)}

    if proc.returncode == 0:
        return {"success": True, "message": "Disconnected"}
    
    err = (proc.stderr or proc.stdout or "").strip()
    return {"success": False, "message": err or "Unknown error"}
