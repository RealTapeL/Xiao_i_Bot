import psutil
import time
import threading
import logging
from typing import Dict, Any, Optional
from pynput import mouse, keyboard
from datetime import datetime

try:
    from AppKit import NSWorkspace
except ImportError:
    NSWorkspace = None

logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统状态监控模块"""

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.running = False
        self.stats: Dict[str, Any] = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "net_io": {"sent": 0, "recv": 0},
            "active_app": "Unknown",
            "last_input_time": time.time(),
            "idle_seconds": 0,
            "keyboard_count": 0,
            "mouse_count": 0,
            "timestamp": datetime.now()
        }
        
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._mouse_listener = None
        self._keyboard_listener = None

    def _on_move(self, x, y):
        with self._lock:
            self.stats["last_input_time"] = time.time()
            self.stats["mouse_count"] += 1

    def _on_click(self, x, y, button, pressed):
        if pressed:
            with self._lock:
                self.stats["last_input_time"] = time.time()
                self.stats["mouse_count"] += 1

    def _on_press(self, key):
        with self._lock:
            self.stats["last_input_time"] = time.time()
            self.stats["keyboard_count"] += 1

    def _get_active_app(self) -> str:
        if NSWorkspace:
            try:
                active_app = NSWorkspace.sharedWorkspace().activeApplication()
                return active_app.get('NSApplicationName', 'Unknown')
            except Exception as e:
                logger.error(f"Error getting active app: {e}")
                return "Unknown"
        return "Unknown"

    def _update_stats(self):
        while self.running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                net = psutil.net_io_counters()
                
                with self._lock:
                    self.stats["cpu_percent"] = cpu
                    self.stats["memory_percent"] = mem
                    self.stats["net_io"] = {
                        "sent": net.bytes_sent,
                        "recv": net.bytes_recv
                    }
                    self.stats["active_app"] = self._get_active_app()
                    self.stats["idle_seconds"] = time.time() - self.stats["last_input_time"]
                    self.stats["timestamp"] = datetime.now()
                
                # 每隔一段时间重置计数，或者保留计数由触发引擎决定如何处理
                # 这里我们保持计数，直到下次获取后由引擎处理或在这里重置
                
            except Exception as e:
                logger.error(f"Error updating system stats: {e}")
            
            time.sleep(self.interval)

    def start(self):
        """启动监控"""
        if self.running:
            return
        
        self.running = True
        
        # 启动输入监听器
        self._mouse_listener = mouse.Listener(on_move=self._on_move, on_click=self._on_click)
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        
        self._mouse_listener.start()
        self._keyboard_listener.start()
        
        # 启动状态更新线程
        self._thread = threading.Thread(target=self._update_stats, daemon=True)
        self._thread.start()
        logger.info("System monitor started")

    def stop(self):
        """停止监控"""
        self.running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("System monitor stopped")

    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前状态快照"""
        with self._lock:
            # 返回副本以防在读取时被修改
            current_stats = self.stats.copy()
            # 获取快照后重置输入计数，以便计算频率
            self.stats["keyboard_count"] = 0
            self.stats["mouse_count"] = 0
            return current_stats
