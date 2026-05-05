import pyautogui
import time

def NEW_TASK() -> bool:
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'alt', 'n')
    return True
