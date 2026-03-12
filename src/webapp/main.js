var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
class Dashboard {
    constructor() {
        this.logsContainer = document.getElementById('logsContainer');
        this.logCountElement = document.getElementById('logCount');
        this.toastElement = document.getElementById('toast');
        this.cpuElement = document.getElementById('cpuValue');
        this.memElement = document.getElementById('memValue');
        this.uptimeElement = document.getElementById('uptimeValue');
        this.init();
    }
    init() {
        var _a, _b, _c;
        // 绑定按钮事件
        (_a = document.getElementById('refreshBtn')) === null || _a === void 0 ? void 0 : _a.addEventListener('click', () => this.refreshAll());
        (_b = document.getElementById('clearBtn')) === null || _b === void 0 ? void 0 : _b.addEventListener('click', () => this.clearLogs());
        // 初始化 Telegram WebApp
        const tg = (_c = window.Telegram) === null || _c === void 0 ? void 0 : _c.WebApp;
        if (tg) {
            tg.ready();
            tg.expand();
            // 设置主题颜色以匹配背景
            tg.setHeaderColor('#1a1a2e');
            tg.setBackgroundColor('#050510');
        }
        // 初始加载
        this.refreshAll();
        // 自动刷新 (每 5 秒)
        setInterval(() => this.refreshAll(), 5000);
    }
    refreshAll() {
        return __awaiter(this, void 0, void 0, function* () {
            yield Promise.all([
                this.fetchLogs(),
                this.fetchStatus()
            ]);
        });
    }
    fetchStatus() {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const response = yield fetch('/api/status');
                if (response.ok) {
                    const status = yield response.json();
                    this.updateStatusUI(status);
                }
            }
            catch (e) {
                console.error('Failed to fetch status:', e);
            }
        });
    }
    updateStatusUI(status) {
        this.cpuElement.textContent = `${status.cpu_percent}%`;
        this.memElement.textContent = `${status.memory_percent}%`;
        this.uptimeElement.textContent = status.uptime_formatted;
        // 简单的颜色变化
        this.cpuElement.style.color = status.cpu_percent > 80 ? '#ff4b4b' : '#00ff88';
        this.memElement.style.color = status.memory_percent > 80 ? '#ff4b4b' : '#00ff88';
    }
    fetchLogs() {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const response = yield fetch('/api/logs');
                if (!response.ok)
                    throw new Error('Failed to fetch logs');
                const data = yield response.json();
                this.renderLogs(data.logs || []);
            }
            catch (e) {
                console.error("Fetch logs failed:", e);
                // 仅在首次加载失败时显示错误，避免轮询时频繁打扰
                if (this.logsContainer.innerHTML.includes('Loading')) {
                    this.logsContainer.innerHTML = '<div class="log-entry error">Connection failed. Retrying...</div>';
                }
            }
        });
    }
    renderLogs(logs) {
        // 如果没有新日志且已有内容，则不重新渲染（优化性能）
        // 这里简单地全量渲染，实际生产环境应该做 diff
        if (logs.length === 0) {
            this.logsContainer.innerHTML = '<div style="padding:20px;text-align:center;color:#666">No logs available</div>';
            this.logCountElement.textContent = '0 entries';
            return;
        }
        const html = logs.map(log => {
            const levelClass = log.level.toLowerCase();
            return `
                <div class="log-entry ${levelClass}">
                    <span class="timestamp">${log.timestamp}</span>
                    <span style="color:var(--text-secondary)">[${log.level}]</span>
                    <span class="message">${this.escapeHtml(log.message)}</span>
                </div>
            `;
        }).join('');
        this.logsContainer.innerHTML = html;
        this.logCountElement.textContent = `${logs.length} entries`;
        // 保持滚动在底部
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
    }
    clearLogs() {
        return __awaiter(this, void 0, void 0, function* () {
            if (!confirm('Are you sure you want to clear all system logs?'))
                return;
            try {
                const response = yield fetch('/api/logs/clear', { method: 'POST' });
                if (response.ok) {
                    this.showToast('Logs cleared successfully');
                    this.refreshAll();
                }
                else {
                    this.showToast('Failed to clear logs');
                }
            }
            catch (e) {
                this.showToast('Error connecting to server');
            }
        });
    }
    showToast(message) {
        this.toastElement.textContent = message;
        this.toastElement.classList.add('show');
        setTimeout(() => {
            this.toastElement.classList.remove('show');
        }, 3000);
    }
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}
// 启动应用
new Dashboard();
