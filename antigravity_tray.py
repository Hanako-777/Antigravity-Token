import os
import sys
import threading
import time
import subprocess
import webbrowser
import ctypes
import math
from PIL import Image, ImageDraw
import pystray
import usage_tracker

APP_DIR = os.path.dirname(os.path.abspath(__file__))
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

HUD_PROFILE = os.path.join(APP_DIR, ".hud_profile")

WIN_WIDTH = 680
WIN_HEIGHT = 680

def get_bottom_right_position(win_w=WIN_WIDTH, win_h=WIN_HEIGHT):
    try:
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        rect = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        work_w = rect.right - rect.left
        work_h = rect.bottom - rect.top
        pos_x = max(0, rect.left + work_w - win_w - 16)
        pos_y = max(0, rect.top + work_h - win_h - 12)
        return pos_x, pos_y
    except Exception:
        return 1220, 340

def create_tray_icon():
    # Solid vibrant Gemini sparkle star with Blue-to-Pink gradient on 100% TRANSPARENT background
    size = 256
    cx, cy = 128, 128
    R = 118

    points = []
    steps_per_quarter = 36
    for q in range(4):
        for i in range(steps_per_quarter):
            t = i / steps_per_quarter
            angle = (q + t) * (math.pi / 2)
            ca = math.cos(angle)
            sa = math.sin(angle)
            p = 2.6
            x = cx + R * (abs(ca) ** p) * (1 if ca >= 0 else -1)
            y = cy + R * (abs(sa) ** p) * (1 if sa >= 0 else -1)
            points.append((x, y))

    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    # 100% solid star, NO hollow center
    mask_draw.polygon(points, fill=255)

    # Blue to Pink gradient:
    # Blue (#2563eb: 37, 99, 235) -> Pink/Rose (#f43f5e / #ec4899: 240, 70, 150)
    grad = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    for y in range(size):
        for x in range(size):
            factor = (x + y) / (2 * size)
            r = int(37 * (1 - factor) + 240 * factor)
            g = int(99 * (1 - factor) + 70 * factor)
            b = int(235 * (1 - factor) + 150 * factor)
            grad.putpixel((x, y), (r, g, b, 255))
    grad.putalpha(mask)

    return grad.resize((64, 64), Image.Resampling.LANCZOS)

def get_tooltip_text():
    try:
        daily, total = usage_tracker.analyze_usage()
        today_str = time.strftime("%Y-%m-%d")
        today_item = daily.get(today_str, {"input": 0, "output": 0, "turns": 0})
        today_tot = today_item["input"] + today_item["output"]
        grand_tot = total["input"] + total["output"]
        return f"Antigravity Token\n今日消耗: {usage_tracker.format_tokens(today_tot)} ({today_tot:,})\n历史累计: {usage_tracker.format_tokens(grand_tot)}\n点击打开独立统计看板"
    except Exception:
        return "Antigravity Token (点击查看用量)"

def open_dashboard():
    try:
        daily, total = usage_tracker.analyze_usage()
        html_file = usage_tracker.build_codex_style_html(daily, total)
        file_url = f"file:///{html_file.replace(chr(92), '/')}"
        pos_x, pos_y = get_bottom_right_position(WIN_WIDTH, WIN_HEIGHT)
        
        # Launch dedicated Edge App instance with custom profile to strictly enforce position & size
        if os.path.exists(EDGE_PATH):
            subprocess.Popen([
                EDGE_PATH,
                f"--app={file_url}",
                f"--user-data-dir={HUD_PROFILE}",
                f"--window-size={WIN_WIDTH},{WIN_HEIGHT}",
                f"--window-position={pos_x},{pos_y}",
                "--no-first-run",
                "--no-default-browser-check"
            ])
        else:
            webbrowser.open(file_url)
    except Exception:
        pass

def main():
    def on_click(icon, item):
        open_dashboard()

    def on_exit(icon, item):
        icon.stop()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("打开 Antigravity Token 看板", on_click, default=True),
        pystray.MenuItem("退出", on_exit)
    )

    icon = pystray.Icon("AntigravityToken", create_tray_icon(), get_tooltip_text(), menu)

    def setup(icon):
        icon.visible = True
        def update_loop():
            while icon.visible:
                try:
                    icon.title = get_tooltip_text()
                except Exception:
                    pass
                time.sleep(30)
        t = threading.Thread(target=update_loop, daemon=True)
        t.start()

    icon.run(setup=setup)

if __name__ == "__main__":
    main()
