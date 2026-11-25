"""Application path conventions (placeholder).

No logic yet. This module fixes the intent:

    APP_NAME           = "proton-wg-manager"
    CONFIG_DIR         = ~/.config/proton-wg-manager        (Assignment 13)
    SETTINGS_FILE      = CONFIG_DIR / "settings.json"       (Assignment 13)
    WIREGUARD_DIR      = /etc/wireguard                     (Assignment 06)

The settings file must be created with mode 0600 because it may
later hold user preferences referencing privileged paths.
"""

from __future__ import annotations

APP_NAME = "proton-wg-manager"
