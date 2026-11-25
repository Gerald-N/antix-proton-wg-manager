"""Logging and redaction utilities."""
from __future__ import annotations

import logging
import re
from pathlib import Path

# Ensure config directory exists
LOG_DIR = Path.home() / ".config" / "wifi-vpn"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "wifi-vpn.log"

logger = logging.getLogger("wifi-vpn")
logger.setLevel(logging.DEBUG)

# Log to file
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Also log to console if running in terminal
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

# Matches "PrivateKey = ...", "PresharedKey = ...", including leading whitespace
_KEY_REGEX = re.compile(r"^(\s*(?:PrivateKey|PresharedKey)\s*=\s*).*$", re.IGNORECASE | re.MULTILINE)

def redact(text: str) -> str:
    """Replaces any secret keys in the text with '<REDACTED>'."""
    if not text:
        return text
    return _KEY_REGEX.sub(r"\1<REDACTED>", text)

def safe_log(msg: str, level: int = logging.INFO) -> None:
    """Logs a message after applying redaction."""
    logger.log(level, redact(msg))
