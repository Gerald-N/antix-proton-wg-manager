# Wi-Fi & VPN Manager for antiX / Debian 12

A lightweight, native GTK 3 application for managing Wi-Fi connections (via NetworkManager) and WireGuard VPNs (via wg-quick). 

Designed specifically for antiX Linux, IceWM, and LXQt environments where modern desktop environments (GNOME/KDE) and systemd are absent.

## Features
- **VPN Management:** Import and connect WireGuard `.conf` profiles securely using `pkexec` (or `sudo` in dev mode).
- **Wi-Fi Management:** Scan, connect, and disconnect from Wi-Fi networks using `nmcli`.
- **System Tray Applet:** Runs in the background with a system tray icon indicating connection status. Quick-connect options via right-click menu.
- **No systemd required:** Uses `elogind` and standard sysvinit compatibility.

## Installation (Development)

### Dependencies
Ensure you have the required system packages:
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 wireguard-tools network-manager ssh-askpass

### Clone and Run
git clone https://github.com/yourusername/wifi-vpn.git
cd wifi-vpn
python3 main.py

## Autostart (Tray Applet)
To have the applet start automatically in your system tray when you log in:
1. Copy the desktop entry to your autostart folder:
   cp wifi-vpn-autostart.desktop ~/.config/autostart/
2. Edit the path inside ~/.config/autostart/wifi-vpn-autostart.desktop to point to where you cloned the repo.

## Debugging
If the app fails to connect, check the log file:
cat ~/.config/wifi-vpn/wifi-vpn.log
(Note: Private keys are automatically redacted from this log).

## Security
- The app never stores your Wi-Fi passwords or WireGuard private keys directly.
- Wi-Fi authentication is handled entirely by NetworkManager.
- VPN configuration is handled entirely by wg-quick.
- Privileged operations are isolated to specific whitelisted commands in app/backend/privilege.py.
