import pyautogui
import json
import os
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(SCRIPT_DIR, "mouse_pos.json")

def INT_TRAE() -> bool:
    if not os.path.exists(POS_FILE):
        get_pos_script = os.path.join(SCRIPT_DIR, "get_mouse_pos.py")
        subprocess.run(["python", get_pos_script])

    with open(POS_FILE, "r", encoding="utf-8") as f:
        pos = json.load(f)

    clicks = pos.get("clicks", [])
    if not clicks:
        return False

    for i, click in enumerate(clicks):
        if i > 0 and "delay" in click:
            time.sleep(click["delay"])
        x = click["abs_x"]
        y = click["abs_y"]
        pyautogui.moveTo(x, y)
        if click["type"] == "left":
            pyautogui.click()
        else:
            pyautogui.click(button='right')
    return True