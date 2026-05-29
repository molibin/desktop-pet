"""从 idle.gif 首帧生成应用图标 (.ico / .png)"""

import os
import sys
from PIL import Image

# 项目根目录
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gif_path = os.path.join(root, "resources", "animations", "idle.gif")
ico_path = os.path.join(root, "resources", "icons", "app.ico")
png_path = os.path.join(root, "resources", "icons", "tray.png")

if os.path.exists(gif_path):
    gif = Image.open(gif_path)
    frame = gif.convert("RGBA")
    frame = frame.resize((128, 128), Image.LANCZOS)
    frame.save(ico_path, format="ICO", sizes=[(32, 32), (64, 64), (128, 128)])
    frame.save(png_path, format="PNG")
    print("OK")
else:
    # 创建空白图标
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    img.save(ico_path, format="ICO", sizes=[(32, 32), (64, 64), (128, 128)])
    img.save(png_path, format="PNG")
    print("OK (blank)")
