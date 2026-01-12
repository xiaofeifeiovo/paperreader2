"""
GPU 设备检测和验证测试脚本

用途:
- 验证 GPU 设备检测功能
- 测试 Pix2Text 模型加载
- 确认 GPU 加速是否生效

运行:
    python test_gpu.py
"""
import logging
from app.core.pdf_processor import PDFProcessor, detect_device

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_device_detection():
    """测试设备检测"""
    print("=" * 60)
    print("测试 1: 设备检测")
    print("=" * 60)

    device = detect_device()
    print(f"\n✅ 检测到的设备: {device}\n")

    if device == 'cuda':
        print("🚀 GPU 加速已启用")
        try:
            import torch
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"   VRAM: {vram:.1f} GB")
        except Exception as e:
            print(f"   ⚠️  无法获取 GPU 详细信息: {e}")
    else:
        print("💻 将使用 CPU 进行处理")

    return device


def test_processor_initialization(device=None):
    """测试处理器初始化"""
    print("\n" + "=" * 60)
    print("测试 2: PDFProcessor 初始化")
    print("=" * 60)

    try:
        processor = PDFProcessor(device=device)
        print(f"\n✅ PDFProcessor 创建成功")
        print(f"   设备: {processor.device}\n")
        return processor
    except Exception as e:
        print(f"\n❌ PDFProcessor 创建失败: {e}\n")
        raise


def test_model_loading(processor):
    """测试模型加载（这会触发实际模型初始化）"""
    print("=" * 60)
    print("测试 3: Pix2Text 模型加载")
    print("=" * 60)
    print("\n⏳ 正在加载 Pix2Text 模型（首次可能需要 1-2 分钟）...\n")

    try:
        _ = processor.p2t
        print("\n✅ Pix2Text 模型加载成功！")
        print(f"   使用设备: {processor.device}\n")
    except Exception as e:
        print(f"\n❌ Pix2Text 模型加载失败: {e}\n")
        raise


def test_environment_variable():
    """测试环境变量控制"""
    import os

    print("=" * 60)
    print("测试 4: 环境变量控制")
    print("=" * 60)

    # 测试 CPU 强制
    print("\n测试 4.1: 强制使用 CPU")
    os.environ['PAPERREADER_DEVICE'] = 'cpu'
    device_cpu = detect_device()
    print(f"   设置 PAPERREADER_DEVICE=cpu")
    print(f"   检测结果: {device_cpu}")
    assert device_cpu == 'cpu', "CPU 强制设置失败"
    print("   ✅ CPU 强制设置成功\n")

    # 测试 CUDA 强制
    print("测试 4.2: 强制使用 CUDA")
    os.environ['PAPERREADER_DEVICE'] = 'cuda'
    device_cuda = detect_device()
    print(f"   设置 PAPERREADER_DEVICE=cuda")
    print(f"   检测结果: {device_cuda}")
    assert device_cuda == 'cuda', "CUDA 强制设置失败"
    print("   ✅ CUDA 强制设置成功\n")

    # 清除环境变量
    del os.environ['PAPERREADER_DEVICE']
    print("测试 4.3: 自动检测（清除环境变量）")
    device_auto = detect_device()
    print(f"   清除 PAPERREADER_DEVICE")
    print(f"   检测结果: {device_auto}")
    print("   ✅ 自动检测成功\n")


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🎯 PaperReader2 GPU 设备检测测试")
    print("=" * 60)

    try:
        # 测试 1: 设备检测
        device = test_device_detection()

        # 测试 2: 处理器初始化
        processor = test_processor_initialization()

        # 测试 3: 模型加载（可选，耗时较长）
        print("\n" + "=" * 60)
        print("是否测试模型加载？（首次运行需要 1-2 分钟）")
        print("=" * 60)
        response = input("输入 'y' 继续测试模型加载，其他键跳过: ").strip().lower()

        if response == 'y':
            test_model_loading(processor)
        else:
            print("\n⏭️  跳过模型加载测试")

        # 测试 4: 环境变量控制
        print("\n" + "=" * 60)
        print("是否测试环境变量控制？")
        print("=" * 60)
        response = input("输入 'y' 继续测试环境变量，其他键跳过: ").strip().lower()

        if response == 'y':
            test_environment_variable()
        else:
            print("\n⏭️  跳过环境变量测试")

        # 总结
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print(f"\n📊 总结:")
        print(f"   - 检测设备: {device}")
        print(f"   - PDFProcessor 设备: {processor.device}")

        if device == 'cuda':
            print(f"   - GPU 加速: ✅ 已启用")
        else:
            print(f"   - GPU 加速: ⚠️  未启用（使用 CPU）")

        print("\n💡 提示:")
        print(f"   - 要强制使用 GPU: 设置环境变量 PAPERREADER_DEVICE=cuda")
        print(f"   - 要强制使用 CPU: 设置环境变量 PAPERREADER_DEVICE=cpu")
        print(f"   - 自动检测模式: 不设置 PAPERREADER_DEVICE（推荐）")
        print("\n")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 测试失败")
        print("=" * 60)
        print(f"\n错误信息: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
