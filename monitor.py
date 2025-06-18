#!/usr/bin/env python3
"""
监控脚本 - 用于监控Feishu Chat-Ops应用的运行状态

功能：
1. 应用健康检查
2. 性能监控
3. 日志分析
4. 告警通知
5. 自动重启

使用方法：
    python monitor.py --check-health
    python monitor.py --monitor --interval 60
    python monitor.py --analyze-logs
    python monitor.py --auto-restart
"""

import os
import sys
import time
import json
import argparse
import logging
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import threading
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """健康状态数据类"""
    is_healthy: bool
    response_time: float
    status_code: int
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_connections: int
    response_time: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ApplicationMonitor:
    """应用监控器"""
    
    def __init__(self, 
                 app_url: str = "http://localhost:8000",
                 log_dir: str = "logs",
                 alert_webhook: str = None):
        self.app_url = app_url
        self.log_dir = Path(log_dir)
        self.alert_webhook = alert_webhook
        self.health_history: List[HealthStatus] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.process = None
        self._find_process()
    
    def _find_process(self):
        """查找应用进程"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    self.process = proc
                    logger.info(f"找到应用进程: PID {proc.pid}")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    def check_health(self) -> HealthStatus:
        """检查应用健康状态"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.app_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                health_status = HealthStatus(
                    is_healthy=True,
                    response_time=response_time,
                    status_code=response.status_code
                )
            else:
                health_status = HealthStatus(
                    is_healthy=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"HTTP {response.status_code}"
                )
        
        except requests.exceptions.RequestException as e:
            health_status = HealthStatus(
                is_healthy=False,
                response_time=0,
                status_code=0,
                error_message=str(e)
            )
        
        self.health_history.append(health_status)
        
        # 保持历史记录在合理范围内
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
        
        return health_status
    
    def get_performance_metrics(self) -> Optional[PerformanceMetrics]:
        """获取性能指标"""
        if not self.process:
            self._find_process()
            if not self.process:
                logger.warning("未找到应用进程")
                return None
        
        try:
            # CPU和内存使用率
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # 磁盘使用率
            disk_usage = psutil.disk_usage('/')
            disk_usage_percent = disk_usage.percent
            
            # 网络连接数
            try:
                connections = len(self.process.connections())
            except psutil.AccessDenied:
                connections = 0
            
            # 响应时间
            health_status = self.check_health()
            response_time = health_status.response_time
            
            metrics = PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                disk_usage_percent=disk_usage_percent,
                network_connections=connections,
                response_time=response_time
            )
            
            self.performance_history.append(metrics)
            
            # 保持历史记录在合理范围内
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            return metrics
            
        except psutil.NoSuchProcess:
            logger.warning("应用进程已终止")
            self.process = None
            return None
    
    def analyze_logs(self, hours: int = 24) -> Dict:
        """分析日志文件"""
        logger.info(f"分析最近{hours}小时的日志...")
        
        analysis = {
            "total_lines": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "recent_errors": [],
            "error_patterns": {},
            "performance_issues": []
        }
        
        # 查找日志文件
        log_files = []
        if self.log_dir.exists():
            log_files.extend(self.log_dir.glob("*.log"))
            log_files.extend(self.log_dir.glob("*.txt"))
        
        # 如果没有找到日志文件，尝试标准位置
        if not log_files:
            possible_locations = [
                Path("app.log"),
                Path("application.log"),
                Path("/var/log/feishu-chatops.log")
            ]
            log_files = [f for f in possible_locations if f.exists()]
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        analysis["total_lines"] += 1
                        
                        # 简单的日志级别检测
                        line_lower = line.lower()
                        if 'error' in line_lower:
                            analysis["error_count"] += 1
                            if len(analysis["recent_errors"]) < 10:
                                analysis["recent_errors"].append(line.strip())
                            
                            # 错误模式分析
                            for pattern in ['database', 'connection', 'timeout', 'api', 'auth']:
                                if pattern in line_lower:
                                    analysis["error_patterns"][pattern] = analysis["error_patterns"].get(pattern, 0) + 1
                        
                        elif 'warning' in line_lower:
                            analysis["warning_count"] += 1
                        elif 'info' in line_lower:
                            analysis["info_count"] += 1
                        
                        # 性能问题检测
                        if 'slow' in line_lower or 'timeout' in line_lower:
                            analysis["performance_issues"].append(line.strip())
            
            except Exception as e:
                logger.error(f"读取日志文件失败 {log_file}: {e}")
        
        return analysis
    
    def send_alert(self, message: str, level: str = "warning"):
        """发送告警通知"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "app_url": self.app_url
        }
        
        logger.warning(f"告警: {message}")
        
        # 如果配置了Webhook，发送通知
        if self.alert_webhook:
            try:
                requests.post(
                    self.alert_webhook,
                    json=alert_data,
                    timeout=10
                )
            except Exception as e:
                logger.error(f"发送告警失败: {e}")
    
    def check_alerts(self, metrics: PerformanceMetrics, health: HealthStatus):
        """检查是否需要告警"""
        # 健康检查告警
        if not health.is_healthy:
            self.send_alert(
                f"应用健康检查失败: {health.error_message}",
                "critical"
            )
        
        # 响应时间告警
        if health.response_time > 5.0:  # 5秒
            self.send_alert(
                f"响应时间过长: {health.response_time:.2f}秒",
                "warning"
            )
        
        if metrics:
            # CPU使用率告警
            if metrics.cpu_percent > 80:
                self.send_alert(
                    f"CPU使用率过高: {metrics.cpu_percent:.1f}%",
                    "warning"
                )
            
            # 内存使用率告警
            if metrics.memory_percent > 80:
                self.send_alert(
                    f"内存使用率过高: {metrics.memory_percent:.1f}%",
                    "warning"
                )
            
            # 磁盘使用率告警
            if metrics.disk_usage_percent > 90:
                self.send_alert(
                    f"磁盘使用率过高: {metrics.disk_usage_percent:.1f}%",
                    "critical"
                )
    
    def restart_application(self) -> bool:
        """重启应用"""
        logger.info("尝试重启应用...")
        
        try:
            # 停止当前进程
            if self.process:
                logger.info(f"停止进程 PID {self.process.pid}")
                self.process.terminate()
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    logger.warning("进程未在10秒内结束，强制终止")
                    self.process.kill()
            
            # 启动新进程
            logger.info("启动新进程...")
            subprocess.Popen([sys.executable, "main.py"], 
                           cwd=os.getcwd(),
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            
            # 等待一段时间让应用启动
            time.sleep(5)
            
            # 重新查找进程
            self._find_process()
            
            # 验证重启是否成功
            health = self.check_health()
            if health.is_healthy:
                logger.info("应用重启成功")
                self.send_alert("应用已成功重启", "info")
                return True
            else:
                logger.error("应用重启后健康检查失败")
                self.send_alert("应用重启失败", "critical")
                return False
        
        except Exception as e:
            logger.error(f"重启应用失败: {e}")
            self.send_alert(f"应用重启失败: {e}", "critical")
            return False
    
    def monitor_loop(self, interval: int = 60, auto_restart: bool = False):
        """监控循环"""
        logger.info(f"开始监控，检查间隔: {interval}秒")
        
        consecutive_failures = 0
        max_failures = 3
        
        try:
            while True:
                # 健康检查
                health = self.check_health()
                
                # 性能指标
                metrics = self.get_performance_metrics()
                
                # 检查告警
                self.check_alerts(metrics, health)
                
                # 输出状态
                status = "✅" if health.is_healthy else "❌"
                logger.info(
                    f"{status} 健康状态: {health.is_healthy}, "
                    f"响应时间: {health.response_time:.2f}s"
                )
                
                if metrics:
                    logger.info(
                        f"📊 CPU: {metrics.cpu_percent:.1f}%, "
                        f"内存: {metrics.memory_percent:.1f}% ({metrics.memory_mb:.1f}MB), "
                        f"连接数: {metrics.network_connections}"
                    )
                
                # 自动重启逻辑
                if auto_restart:
                    if not health.is_healthy:
                        consecutive_failures += 1
                        logger.warning(f"连续失败次数: {consecutive_failures}/{max_failures}")
                        
                        if consecutive_failures >= max_failures:
                            logger.warning("达到最大失败次数，尝试重启应用")
                            if self.restart_application():
                                consecutive_failures = 0
                            else:
                                # 重启失败，等待更长时间
                                time.sleep(interval * 2)
                                continue
                    else:
                        consecutive_failures = 0
                
                # 等待下次检查
                time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("监控已停止")
    
    def generate_report(self) -> Dict:
        """生成监控报告"""
        if not self.health_history or not self.performance_history:
            return {"error": "没有足够的监控数据"}
        
        # 计算统计信息
        recent_health = self.health_history[-100:]  # 最近100次检查
        recent_performance = self.performance_history[-100:]
        
        healthy_count = sum(1 for h in recent_health if h.is_healthy)
        uptime_percentage = (healthy_count / len(recent_health)) * 100
        
        avg_response_time = sum(h.response_time for h in recent_health if h.is_healthy) / max(healthy_count, 1)
        
        avg_cpu = sum(p.cpu_percent for p in recent_performance) / len(recent_performance)
        avg_memory = sum(p.memory_percent for p in recent_performance) / len(recent_performance)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "uptime_percentage": round(uptime_percentage, 2),
            "average_response_time": round(avg_response_time, 3),
            "average_cpu_usage": round(avg_cpu, 2),
            "average_memory_usage": round(avg_memory, 2),
            "total_health_checks": len(self.health_history),
            "total_performance_samples": len(self.performance_history),
            "current_status": {
                "healthy": recent_health[-1].is_healthy if recent_health else False,
                "last_check": recent_health[-1].timestamp.isoformat() if recent_health else None
            }
        }
        
        return report
    
    def save_metrics(self, filename: str = None):
        """保存监控指标到文件"""
        if filename is None:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "health_history": [
                {
                    "timestamp": h.timestamp.isoformat(),
                    "is_healthy": h.is_healthy,
                    "response_time": h.response_time,
                    "status_code": h.status_code,
                    "error_message": h.error_message
                }
                for h in self.health_history
            ],
            "performance_history": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "cpu_percent": p.cpu_percent,
                    "memory_percent": p.memory_percent,
                    "memory_mb": p.memory_mb,
                    "disk_usage_percent": p.disk_usage_percent,
                    "network_connections": p.network_connections,
                    "response_time": p.response_time
                }
                for p in self.performance_history
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"监控指标已保存到: {filename}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Feishu Chat-Ops 监控脚本')
    parser.add_argument('--app-url', default='http://localhost:8000', help='应用URL')
    parser.add_argument('--log-dir', default='logs', help='日志目录')
    parser.add_argument('--alert-webhook', help='告警Webhook URL')
    
    # 操作选项
    parser.add_argument('--check-health', action='store_true', help='执行健康检查')
    parser.add_argument('--monitor', action='store_true', help='启动监控')
    parser.add_argument('--analyze-logs', action='store_true', help='分析日志')
    parser.add_argument('--restart', action='store_true', help='重启应用')
    parser.add_argument('--report', action='store_true', help='生成报告')
    parser.add_argument('--save-metrics', help='保存监控指标到文件')
    
    # 监控选项
    parser.add_argument('--interval', type=int, default=60, help='监控间隔（秒）')
    parser.add_argument('--auto-restart', action='store_true', help='自动重启')
    parser.add_argument('--log-hours', type=int, default=24, help='日志分析时间范围（小时）')
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = ApplicationMonitor(
        app_url=args.app_url,
        log_dir=args.log_dir,
        alert_webhook=args.alert_webhook
    )
    
    # 执行操作
    if args.check_health:
        health = monitor.check_health()
        print(f"健康状态: {'✅ 正常' if health.is_healthy else '❌ 异常'}")
        print(f"响应时间: {health.response_time:.3f}秒")
        print(f"状态码: {health.status_code}")
        if health.error_message:
            print(f"错误信息: {health.error_message}")
    
    elif args.monitor:
        monitor.monitor_loop(args.interval, args.auto_restart)
    
    elif args.analyze_logs:
        analysis = monitor.analyze_logs(args.log_hours)
        print(f"\n📊 日志分析报告（最近{args.log_hours}小时）")
        print(f"总行数: {analysis['total_lines']}")
        print(f"错误数: {analysis['error_count']}")
        print(f"警告数: {analysis['warning_count']}")
        print(f"信息数: {analysis['info_count']}")
        
        if analysis['error_patterns']:
            print("\n错误模式:")
            for pattern, count in analysis['error_patterns'].items():
                print(f"  {pattern}: {count}")
        
        if analysis['recent_errors']:
            print("\n最近错误:")
            for error in analysis['recent_errors'][:5]:
                print(f"  {error}")
    
    elif args.restart:
        success = monitor.restart_application()
        print(f"重启结果: {'✅ 成功' if success else '❌ 失败'}")
    
    elif args.report:
        report = monitor.generate_report()
        print("\n📈 监控报告")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    elif args.save_metrics:
        monitor.save_metrics(args.save_metrics)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()