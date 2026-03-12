import logging
import os
import json
import psutil
import time
from datetime import datetime
from aiohttp import web
from typing import List, Dict

# 配置 web server 的 logger
logger = logging.getLogger(__name__)

# 降低 aiohttp.access 日志级别，减少干扰
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

class WebServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 8080, log_file: str = 'bot.log'):
        self.host = host
        self.port = port
        self.log_file = log_file
        self.start_time = time.time()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        # API 路由
        self.app.router.add_get('/api/logs', self.handle_get_logs)
        self.app.router.add_post('/api/logs/clear', self.handle_clear_logs)
        self.app.router.add_get('/api/status', self.handle_get_status)
        
        # 静态文件服务
        static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp')
        
        # 将首页作为默认路由
        self.app.router.add_get('/', self.handle_index)
        
        # 提供静态资源
        self.app.router.add_static('/assets/', static_path, show_index=True)
        # 将 JS 和 CSS 文件单独添加路由，或者直接让 webapp 目录下的文件可访问
        self.app.router.add_static('/', static_path)

    async def handle_index(self, request):
        return web.FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp', 'index.html'))

    async def handle_get_status(self, request):
        """获取系统状态 API"""
        try:
            process = psutil.Process(os.getpid())
            uptime = time.time() - self.start_time
            
            # 格式化运行时间
            m, s = divmod(int(uptime), 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            if d > 0:
                uptime_str = f"{d}d {h}h {m}m"
            elif h > 0:
                uptime_str = f"{h}h {m}m"
            else:
                uptime_str = f"{m}m {s}s"
            
            status = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'process_memory_mb': process.memory_info().rss / 1024 / 1024,
                'uptime_seconds': int(uptime),
                'uptime_formatted': uptime_str
            }
            return web.json_response(status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_clear_logs(self, request):
        """清空日志 API"""
        try:
            if os.path.exists(self.log_file):
                # 清空文件内容
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} - WebServer - INFO - Logs cleared via Web Interface\n")
                return web.json_response({'success': True, 'message': 'Logs cleared successfully'})
            else:
                return web.json_response({'success': False, 'message': 'Log file not found'}, status=404)
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_logs(self, request):
        """获取日志 API"""
        try:
            # 读取日志文件，这里假设日志文件在项目根目录
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot.log')
            self.log_file = log_path
            
            logs = self.read_logs()
            return web.json_response({'logs': logs})
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return web.json_response({'error': str(e)}, status=500)

    def read_logs(self, limit: int = 100) -> List[Dict[str, str]]:
        """读取最近的日志"""
        logs = []
        if not os.path.exists(self.log_file):
            return logs

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 获取最后 N 行
                recent_lines = lines[-limit:]
                
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # 尝试解析日志格式：YYYY-MM-DD HH:MM:SS,mmm - logger - LEVEL - message
                        parts = line.split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp = parts[0]
                            # logger_name = parts[1]
                            level = parts[2]
                            message = parts[3].strip()
                            
                            logs.append({
                                'timestamp': timestamp,
                                'level': level,
                                'message': message
                            })
                        else:
                            # 无法解析的行作为普通消息
                            logs.append({
                                'timestamp': '',
                                'level': 'INFO',
                                'message': line
                            })
                    except Exception:
                        logs.append({
                            'timestamp': '',
                            'level': 'INFO',
                            'message': line
                        })
        except Exception as e:
            logger.error(f"Failed to parse log file: {e}")
            
        return logs

    def run(self):
        """运行 Web 服务器 (阻塞模式)"""
        web.run_app(self.app, host=self.host, port=self.port)

    async def start(self):
        """异步启动 Web 服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"Web server started at http://{self.host}:{self.port}")
