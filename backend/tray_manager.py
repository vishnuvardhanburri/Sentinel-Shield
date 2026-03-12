import os
import sys
import logging
import subprocess

import pystray
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ICON_PATH = os.path.join(os.path.dirname(__file__), "shield_icon.png")
SHIELD_SH = os.path.join(BASE_DIR, "shield.sh")
SHIELD_BAT = os.path.join(BASE_DIR, "shield.bat")
ALERT_LOG = os.path.join(BASE_DIR, "logs", "alerts.log")
TRAY_LOG = os.path.join(BASE_DIR, "logs", "tray_output.log")

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(filename=TRAY_LOG, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _run_status_terminal():
    """Open status view in a platform-native terminal."""
    try:
        if sys.platform == "darwin":
            cmd = f"sh '{SHIELD_SH}' status"
            subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script "{cmd}"'], check=False)
        elif os.name == "nt":
            subprocess.Popen(["cmd", "/c", "start", "", "cmd", "/k", f'"{SHIELD_BAT}" status'], shell=False)
        else:
            # Linux best-effort terminal launchers.
            for terminal in (["x-terminal-emulator", "-e"], ["gnome-terminal", "--"], ["konsole", "-e"]):
                try:
                    subprocess.Popen(terminal + [f"{SHIELD_SH}", "status"])
                    return
                except FileNotFoundError:
                    continue
            logging.warning("No supported Linux terminal found for status command")
    except Exception as exc:
        logging.error("Status launch failed: %s", exc)


def on_status(icon, item):
    _run_status_terminal()


def on_logs(icon, item):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", "TextEdit", ALERT_LOG], check=False)
        elif os.name == "nt":
            subprocess.Popen(["notepad.exe", ALERT_LOG])
        else:
            subprocess.Popen(["xdg-open", ALERT_LOG])
    except Exception as exc:
        logging.error("Log viewer launch failed: %s", exc)


def on_stop(icon, item):
    try:
        if os.name == "nt":
            subprocess.run(["cmd", "/c", SHIELD_BAT, "stop"], check=False)
        else:
            subprocess.run([SHIELD_SH, "stop"], check=False)
    finally:
        icon.stop()


def setup():
    if os.path.exists(ICON_PATH):
        image = Image.open(ICON_PATH)
    else:
        image = Image.new("RGB", (64, 64), (16, 185, 129))

    menu = pystray.Menu(
        pystray.MenuItem("Sentinel Status", on_status),
        pystray.MenuItem("View Alert Logs", on_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Deactivate Shield", on_stop),
    )

    icon = pystray.Icon("SentinelShield", image, "Sentinel Shield Active", menu)
    icon.run()


if __name__ == "__main__":
    setup()
