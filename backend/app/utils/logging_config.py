"""
日志配置模块
提供统一的日志格式和配置

功能:
- 彩色日志输出(带emoji标识)
- 支持终端和文件输出
- 自动配置第三方库日志级别
"""
import logging
import sys
from pathlib import Path
from typing import Optional


# Emoji图标映射
LOG_ICONS = {
    "INFO": "ℹ️",
    "DEBUG": "🔍",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🚨",
}


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器

    为不同级别的日志添加emoji和颜色标识
    格式: 时间 [级别emoji] [模块名] 消息
    """

    def __init__(self, *args, use_color: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

        # ANSI颜色代码
        self.COLORS = {
            "DEBUG": "\033[36m",    # 青色
            "INFO": "\033[37m",     # 白色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",    # 红色
            "CRITICAL": "\033[35m", # 紫色
            "RESET": "\033[0m",
        }

    def format(self, record):
        """格式化日志记录

        1. 添加emoji图标到级别名
        2. 添加颜色(如果启用)
        3. 应用标准格式化
        """
        # 添加emoji图标
        icon = LOG_ICONS.get(record.levelname, "")
        original_levelname = record.levelname
        record.levelname = f"{icon} {original_levelname}"

        # 调用父类格式化
        log_message = super().format(record)

        # 添加颜色(如果支持且启用)
        if self.use_color and sys.stderr.isatty():
            level_color = self.COLORS.get(original_levelname, "")
            log_message = f"{level_color}{log_message}{self.COLORS['RESET']}"

        return log_message


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    use_color: bool = True
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径 (None表示仅输出到终端)
        use_color: 是否使用彩色输出(终端)

    示例:
        setup_logging(log_level="INFO")  # 仅终端输出
        setup_logging(log_level="DEBUG", log_file=Path("logs/app.log"))  # 终端+文件
    """
    # 转换日志级别字符串为大写
    log_level = log_level.upper()

    # 验证日志级别
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        raise ValueError(f"无效的日志级别: {log_level}. 必须是: {valid_levels}")

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # 清除现有处理器
    root_logger.handlers.clear()

    # ===== 终端处理器 =====
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)  # 处理所有级别的日志

    # 终端格式: 时间 [级别] [模块] 消息
    console_format = ColoredFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        use_color=use_color
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # ===== 文件处理器(可选) =====
    if log_file:
        # 创建日志目录
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 文件处理器(包含更多调试信息)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 文件格式(不带颜色,包含函数名和行号)
        file_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

    # ===== 配置第三方库日志级别(降低噪音) =====
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("pix2text").setLevel(logging.INFO)
    logging.getLogger("pymupdf").setLevel(logging.WARNING)

    # 启动日志
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 日志系统初始化完成: level={log_level}, file={log_file or '仅终端'}")


if __name__ == "__main__":
    """测试日志配置"""
    # 测试彩色输出
    setup_logging(log_level="DEBUG")

    logger = logging.getLogger("test.module")

    logger.debug("这是DEBUG级别的日志")
    logger.info("这是INFO级别的日志")
    logger.warning("这是WARNING级别的日志")
    logger.error("这是ERROR级别的日志")
