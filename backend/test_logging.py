"""
测试日志系统
验证日志配置和输出是否正常工作
"""
import sys
from pathlib import Path

# 添加app目录到Python路径
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.utils.logging_config import setup_logging
from app.utils.performance import monitor_performance
import logging

# 测试不同级别的日志
def test_log_levels():
    """测试不同级别的日志输出"""
    print("\n" + "="*60)
    print("测试1: 日志级别测试")
    print("="*60 + "\n")

    # 初始化日志系统
    setup_logging(log_level="DEBUG")

    logger = logging.getLogger("test.module")

    logger.debug("这是DEBUG级别的日志 - 详细的技术信息")
    logger.info("这是INFO级别的日志 - 关键业务流程")
    logger.warning("这是WARNING级别的日志 - 潜在问题")
    logger.error("这是ERROR级别的日志 - 错误异常")
    # logger.critical("这是CRITICAL级别的日志 - 严重错误")

    print("\n" + "✅ 日志级别测试完成\n")


def test_performance_monitor():
    """测试性能监控"""
    print("="*60)
    print("测试2: 性能监控测试")
    print("="*60 + "\n")

    logger = logging.getLogger("test.performance")

    # 测试上下文管理器
    logger.info("开始性能监控测试...")
    with monitor_performance("测试操作"):
        # 模拟工作
        import time
        time.sleep(0.5)
        # 分配一些内存
        data = [i for i in range(1000000)]

    logger.info("性能监控测试完成\n")


def test_colored_output():
    """测试彩色输出"""
    print("="*60)
    print("测试3: 彩色输出测试")
    print("="*60 + "\n")

    logger = logging.getLogger("test.color")

    logger.info("ℹ️ 这是一条信息日志 (白色)")
    logger.debug("🔍 这是一条调试日志 (青色)")
    logger.warning("⚠️ 这是一条警告日志 (黄色)")
    logger.error("❌ 这是一条错误日志 (红色)")

    print("\n✅ 彩色输出测试完成\n")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║   PaperReader2 日志系统测试            ║
    ╚════════════════════════════════════════╝
    """)

    try:
        test_log_levels()
        test_performance_monitor()
        test_colored_output()

        print("="*60)
        print("✅ 所有测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
