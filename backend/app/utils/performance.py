"""
性能监控工具类
提供内存、CPU、时间等性能指标测量

功能:
- 测量代码块执行时间
- 监控内存使用变化
- 监控CPU使用率
- 提供上下文管理器和类两种使用方式
"""
import time
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 尝试导入psutil,如果不可用则禁用内存/CPU监控
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("⚠️ psutil未安装，性能监控将仅测量时间（pip install psutil）")


class PerformanceMonitor:
    """性能监控器

    测量操作的时间、内存使用和CPU使用率

    属性:
        operation_name: 操作名称
        start_time: 开始时间
        start_memory: 开始时的内存使用(MB)
        process: 当前进程对象(psutil.Process)
    """

    def __init__(self, operation_name: str):
        """
        初始化性能监控器

        Args:
            operation_name: 要监控的操作名称
        """
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.start_memory: Optional[float] = None
        self.end_memory: Optional[float] = None

        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
        else:
            self.process = None

    def start(self) -> None:
        """开始监控"""
        self.start_time = time.time()

        if self.process is not None:
            self.start_memory = self.process.memory_info().rss / 1024 / 1024

        logger.debug(
            f"⏱️ [PERF] {self.operation_name} 开始: "
            f"memory={self.start_memory:.1f}MB" if self.start_memory else f"⏱️ [PERF] {self.operation_name} 开始"
        )

    def stop(self) -> dict:
        """
        停止监控并返回性能指标

        Returns:
            包含性能指标的字典:
            {
                "operation": 操作名称,
                "elapsed_time": 耗时(秒),
                "start_memory_mb": 开始内存(MB),
                "end_memory_mb": 结束内存(MB),
                "memory_delta_mb": 内存变化(MB),
                "cpu_percent": CPU使用率(%)
            }

        Raises:
            RuntimeError: 如果监控未开始就调用stop
        """
        if self.start_time is None:
            raise RuntimeError("监控未开始，请先调用start()")

        # 计算耗时
        elapsed_time = time.time() - self.start_time

        # 计算内存变化
        if self.process is not None:
            self.end_memory = self.process.memory_info().rss / 1024 / 1024
            memory_delta = self.end_memory - self.start_memory
            cpu_percent = self.process.cpu_percent()
        else:
            memory_delta = None
            cpu_percent = None

        # 构建指标字典
        metrics = {
            "operation": self.operation_name,
            "elapsed_time": elapsed_time,
            "start_memory_mb": self.start_memory,
            "end_memory_mb": self.end_memory,
            "memory_delta_mb": memory_delta,
            "cpu_percent": cpu_percent,
        }

        # 记录完成日志
        if memory_delta is not None and cpu_percent is not None:
            logger.info(
                f"📊 [PERF] {self.operation_name} 完成: "
                f"time={elapsed_time:.2f}s, "
                f"memory_delta={memory_delta:+.1f}MB, "
                f"cpu={cpu_percent:.1f}%"
            )
        else:
            logger.info(
                f"📊 [PERF] {self.operation_name} 完成: "
                f"time={elapsed_time:.2f}s"
            )

        return metrics


@contextmanager
def monitor_performance(operation_name: str):
    """
    性能监控上下文管理器

    使用with语句自动监控代码块的性能

    Args:
        operation_name: 操作名称

    示例:
        >>> with monitor_performance("PDF处理"):
        ...     # 处理逻辑
        ...     process_pdf()
        # 自动输出: 📊 [PERF] PDF处理 完成: time=38.57s, memory_delta=+125.3MB
    """
    monitor = PerformanceMonitor(operation_name)
    monitor.start()
    try:
        yield monitor
    finally:
        monitor.stop()


if __name__ == "__main__":
    """测试性能监控"""
    from app.utils.logging_config import setup_logging

    # 初始化日志
    setup_logging(log_level="DEBUG")

    # 测试1: 使用上下文管理器
    logger.info("测试1: 上下文管理器")
    with monitor_performance("测试操作"):
        # 模拟工作
        time.sleep(0.5)
        # 分配一些内存
        data = [i for i in range(1000000)]

    # 测试2: 使用类方法
    logger.info("\n测试2: 类方法")
    monitor = PerformanceMonitor("手动测试")
    monitor.start()
    time.sleep(0.3)
    monitor.stop()

    logger.info("性能监控测试完成")
