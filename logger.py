"""
AYFdiy 轻量日志模块
零依赖，线程安全，ANSI 彩色输出
"""

import sys
import re
import threading
from datetime import datetime


# ==================== ANSI 颜色 ====================
_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLOR_INFO = "\033[38;5;153m"     # 淡蓝色
_COLOR_WARNING = "\033[38;5;214m"  # 橙色


def _paint(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"


# ==================== 线程安全日志器 ====================
class _Logger:
    """线程安全的轻量日志系统"""

    _THREAD_NUM = re.compile(r'(\d+(?:_\d+)?)')

    def __init__(self):
        self._lock = threading.Lock()
        self._color = True
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                self._color = False

    def _fmt(self, message: str, emoji: str, color: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        thread = threading.current_thread().name
        if thread == "MainThread":
            tn = "[Main]".ljust(8)
        else:
            m = self._THREAD_NUM.search(thread)
            tn = f"[T-{m.group(1)}]".ljust(8) if m else "[Work]".ljust(8)
        line = f"[{ts}]{tn} {emoji} {message}"
        return _paint(line, color) if self._color else line

    def info(self, message: str):
        line = self._fmt(message, "ℹ️", _COLOR_INFO)
        with self._lock:
            print(line, flush=True)

    def warning(self, message: str):
        line = self._fmt(message, "⚠️", _COLOR_WARNING)
        with self._lock:
            print(line, flush=True)


# ==================== 全局实例 ====================
logger = _Logger()

__all__ = ['logger']
