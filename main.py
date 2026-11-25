#!/usr/bin/env python3
"""Wi-Fi & VPN Manager — entry point."""
from __future__ import annotations

import os
import sys


def main(argv: list[str] | None = None) -> int:
    import gi
    gi.require_version("Gtk", "3.0")
    from app.gui.application import WifiVpnApplication

    if argv is None:
        argv = sys.argv

    # Intercept --minimized before GTK complains
    if "--minimized" in argv:
        os.environ["WIFI_VPN_MINIMIZED"] = "1"
        argv = [a for a in argv if a != "--minimized"]

    app = WifiVpnApplication()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main())
