import os
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import urllib3
from dotenv import load_dotenv

from jinshi_economic_news_scheduler import EconomicNewsScheduler
from jinshi_flash_fetch import Jin10FlashFetcher
from jinshi_market_statistics_updater import MarketStatisticsUpdater

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --- 1. 高分辨率 (High DPI) 适配 (Windows 环境) ---
def enable_high_dpi():
    try:
        # 适用于 Windows 8.1 及更高版本
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # 适用于 Windows Vista / 7 / 8
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# --- 2. 获取程序当前运行目录 (兼容 PyInstaller 打包后的路径) ---
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，返回 exe 所在文件目录
        return os.path.dirname(sys.executable)
    # 如果是普通 py 脚本运行，返回当前文件目录
    return os.path.dirname(os.path.abspath(__file__))


# 加载同目录下的 .env 文件
env_path = os.path.join(get_base_dir(), '.env')
load_dotenv(dotenv_path=env_path)


# --- GUI 界面 ---
class SchedulerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("数据调度采集系统")

        self.economic_news_schedule = EconomicNewsScheduler()
        self.js_flash_fetcher = Jin10FlashFetcher()
        self.market_stat_updater = MarketStatisticsUpdater()

        # 适当调大默认尺寸以配合 4K/高分屏显示
        self.root.geometry("450x640")

        # 1. 配置 ttk 样式放大按钮尺寸
        style = ttk.Style()
        # 创建自定义样式，继承自 TButton
        style.configure(
            "Big.TButton",
            font=("SimSun", 18, "bold"),  # 增大字号（默认通常为 9~10pt，18pt 接近放大一倍）
            padding=(20, 20)  # 设置内边距 (左右, 上下)，增大按钮高宽
        )

        self.label = ttk.Label(
            root, text="任务状态: 未启动", font=("Microsoft YaHei", 12)
        )
        self.label.pack(pady=25)

        i = 0
        button_text = ["日历抓取", "jinshi新闻", "市场资讯"]
        for title in button_text:
            button = ttk.Button(
                root, text=title,
                command=lambda idx=i, name=title: self.on_click_start(button, idx, name)
            )
            i = i + 1
            button.pack(pady=10, ipady=5, ipadx=10)


    def on_click_start(self, btn_widget:ttk.Button, idx:int, name:str):

        if idx == 0:
            threading.Thread(target=self.economic_news_schedule.run, daemon=True).start()
        elif idx == 1:
            threading.Thread(target=self.js_flash_fetcher.run, daemon=True).start()
        elif idx == 2:
            threading.Thread(target=self.market_stat_updater.run, daemon=True).start()


if __name__ == "__main__":
    # 启用 DPI 高分屏适配
    enable_high_dpi()

    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()