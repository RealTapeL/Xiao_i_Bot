import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TriggerEngine:
    """智能触发引擎 - 根据系统状态判断是否需要发送主动消息"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # 触发冷却时间（秒），防止频繁触发
        self.cooldown_period = self.config.get("cooldown_period", 1800) # 默认30分钟
        self.last_trigger_times: Dict[str, datetime] = {}
        self.last_app: str = "Unknown"
        
        # 阈值配置
        self.idle_threshold = self.config.get("idle_threshold", 300)
        
        # 场景应用分类
        self.scenarios = {
            "gaming": ["Steam", "League of Legends", "Dota 2", "Genshin Impact", "Epic Games", "Minecraft", "World of Warcraft"],
            "working": ["Visual Studio Code", "Xcode", "PyCharm", "Terminal", "iTerm2", "Slack", "Microsoft Teams", "钉钉", "飞书", "Zoom"],
            "entertainment": ["Google Chrome", "Safari", "Microsoft Edge", "Firefox"],
            "media": ["Music", "Spotify", "IINA", "VLC", "NetEaseMusic", "QQMusic"]
        }
        
    def _is_cooling_down(self, reason: str) -> bool:
        if reason not in self.last_trigger_times:
            # 检查全局冷却，防止短时间内发送太多不同类型的消息
            for last_time in self.last_trigger_times.values():
                if (datetime.now() - last_time).total_seconds() < 300: # 全局5分钟冷却
                    return True
            return False
        return (datetime.now() - self.last_trigger_times[reason]).total_seconds() < self.cooldown_period

    def evaluate(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """评估当前状态，决定是否触发消息，并返回触发原因和元数据"""
        
        now = datetime.now()
        idle_secs = stats.get("idle_seconds", 0)
        active_app = stats.get("active_app", "Unknown")
        current_hour = now.hour

        # 1. 空闲 5-15 分钟
        if self.idle_threshold <= idle_secs < 900:
             reason = "idle_short"
             if not self._is_cooling_down(reason):
                 self.last_trigger_times[reason] = now
                 return {
                    "reason": reason,
                    "description": "发呆了吗，在想什么呢？",
                    "message_type": "care"
                 }

        # 2. 空闲超 20 分钟
        if idle_secs >= 1200:
             reason = "idle_long"
             if not self._is_cooling_down(reason):
                 self.last_trigger_times[reason] = now
                 return {
                    "reason": reason,
                    "description": "离开了吗，等你回来~",
                    "message_type": "miss"
                 }

        # 只有在非空闲时才检测应用切换和深夜活跃
        if idle_secs < 60:
            # 3. 深夜还在用电脑 (22:00 - 05:00) - 扩大范围以覆盖 22:00
            if current_hour >= 22 or current_hour < 5:
                reason = "late_night"
                if not self._is_cooling_down(reason):
                    self.last_trigger_times[reason] = now
                    return {
                        "reason": reason,
                        "description": "这么晚了还没睡，注意身体",
                        "message_type": "sleep_advice"
                    }

            # 检测应用变化
            if active_app != self.last_app and active_app != "Unknown":
                prev_app = self.last_app
                self.last_app = active_app
                
                # 4. 检测到打游戏
                if any(game in active_app for game in self.scenarios["gaming"]):
                    reason = "gaming"
                    if not self._is_cooling_down(reason):
                        self.last_trigger_times[reason] = now
                        return {
                            "reason": reason,
                            "description": "在玩游戏啊，记得休息哦",
                            "message_type": "remind"
                        }

                # 5. 切换到工作应用
                if any(work in active_app for work in self.scenarios["working"]):
                    reason = "start_working"
                    if not self._is_cooling_down(reason):
                        self.last_trigger_times[reason] = now
                        return {
                            "reason": reason,
                            "description": "开始工作啦，加油！",
                            "message_type": "encourage"
                        }

                # 6. 工作切换娱乐 (从工作应用切换到浏览器)
                if any(work in prev_app for work in self.scenarios["working"]) and \
                   any(ent in active_app for ent in self.scenarios["entertainment"]):
                    reason = "work_to_fun"
                    if not self._is_cooling_down(reason):
                        self.last_trigger_times[reason] = now
                        return {
                            "reason": reason,
                            "description": "下班了吗，今天辛苦了",
                            "message_type": "comfort"
                        }

                # 7. 看视频/听音乐
                if any(media in active_app for media in self.scenarios["media"]):
                    reason = "media_time"
                    if not self._is_cooling_down(reason):
                        self.last_trigger_times[reason] = now
                        return {
                            "reason": reason,
                            "description": "在看什么好看的吗？",
                            "message_type": "chat"
                        }

        return None
