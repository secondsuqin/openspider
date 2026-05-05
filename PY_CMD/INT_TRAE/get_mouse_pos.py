import tkinter as tk
from tkinter import messagebox
import json
import os
import sys
import time
import ctypes
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(SCRIPT_DIR, "mouse_pos.json")

class MousePosCatcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.recording = False
        self.clicks = []
        self.start_time = None
        self.label = None
        self.status_label = None
        self.btn = None
        self.end_btn = None
        self.monitor_thread = None
        self.running = True
        self.user32 = ctypes.windll.user32

    def start(self):
        self.root.deiconify()
        self.root.title("获取鼠标位置")
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w, win_h = 350, 150
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.label = tk.Label(self.root, text="获取鼠标位置工具", font=("微软雅黑", 12, "bold"), fg="black")
        self.label.pack(pady=5)

        self.status_label = tk.Label(self.root, text="点击 [开始记录] 按钮\n然后点击目标位置（可多次点击）\n最后点击 [结束记录] 保存", font=("微软雅黑", 10), fg="gray")
        self.status_label.pack(pady=5)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.btn = tk.Button(btn_frame, text="开始记录", font=("微软雅黑", 10), bg="#4CAF50", fg="white", width=10, command=self.on_start)
        self.btn.pack(side=tk.LEFT, padx=5)

        self.end_btn = tk.Button(btn_frame, text="结束记录", font=("微软雅黑", 10), bg="#f44336", fg="white", width=10, command=self.on_end, state=tk.DISABLED)
        self.end_btn.pack(side=tk.LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def is_click_on_buttons(self, x, y):
        for widget in [self.btn, self.end_btn]:
            wx1 = widget.winfo_rootx()
            wy1 = widget.winfo_rooty()
            wx2 = wx1 + widget.winfo_width()
            wy2 = wy1 + widget.winfo_height()
            if wx1 <= x <= wx2 and wy1 <= y <= wy2:
                return True
        return False

    def monitor_mouse(self):
        last_pos = None
        last_click_count = 0
        while self.running:
            time.sleep(0.01)
            if not self.recording:
                continue

            try:
                x = ctypes.c_long()
                y = ctypes.c_long()
                self.user32.GetCursorPos(ctypes.byref(x), ctypes.byref(y))
                x, y = x.value, y.value

                if self.is_click_on_buttons(x, y):
                    continue

                VK_LBUTTON = 0x01
                VK_RBUTTON = 0x02
                left_pressed = self.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000
                right_pressed = self.user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000

                if left_pressed or right_pressed:
                    click_type = "left" if left_pressed else "right"
                    delay = time.time() - self.start_time if self.start_time else 0

                    click_data = {
                        "type": click_type,
                        "abs_x": x,
                        "abs_y": y,
                        "delay": round(delay, 3)
                    }
                    self.clicks.append(click_data)
                    self.start_time = time.time()

                    self.root.after(0, self.update_status)
                    time.sleep(0.3)
            except:
                pass

    def update_status(self):
        count = len(self.clicks)
        last = self.clicks[-1]
        self.status_label.config(text=f"已记录 {count} 次点击\n最后: {last['type']}键 - ({last['abs_x']}, {last['abs_y']})\n点击 [结束记录] 完成", fg="blue")

    def on_start(self):
        self.recording = True
        self.clicks = []
        self.start_time = time.time()
        self.btn.config(state=tk.DISABLED, bg="#999999")
        self.end_btn.config(state=tk.NORMAL, bg="#4CAF50")
        self.status_label.config(text="正在记录中...\n请点击目标位置（可多次点击）\n点击 [结束记录] 按钮完成", fg="red")
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()

    def on_end(self):
        self.recording = False
        self.show_result()

    def show_result(self):
        if not self.clicks:
            messagebox.showwarning("提示", "没有记录到任何点击位置")
            self.reset_ui()
            return

        click_info = ""
        for i, c in enumerate(self.clicks, 1):
            click_info += f"第{i}次: {c['type']}键 | 延迟{c['delay']}s | 坐标({c['abs_x']}, {c['abs_y']})\n"

        result = messagebox.askyesno("确认坐标", f"记录了 {len(self.clicks)} 次点击:\n\n{click_info}\n是否保存?")
        if result:
            data = {
                "clicks": self.clicks,
                "count": len(self.clicks)
            }
            with open(POS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完成", f"已保存到:\n{POS_FILE}\n\n共 {len(self.clicks)} 次点击")
        self.reset_ui()

    def reset_ui(self):
        self.btn.config(state=tk.NORMAL, bg="#4CAF50")
        self.end_btn.config(state=tk.DISABLED, bg="#f44336")
        self.status_label.config(text="点击 [开始记录] 按钮\n然后点击目标位置（可多次点击）\n最后点击 [结束记录] 保存", fg="gray")

    def on_close(self):
        self.running = False
        self.root.quit()
        sys.exit()

if __name__ == "__main__":
    catcher = MousePosCatcher()
    catcher.start()
