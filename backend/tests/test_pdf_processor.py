"""
PDF 处理器单元测试
"""
import pytest
import os
from pathlib import Path
from app.core.pdf_processor import PDFProcessor, ProcessingError, detect_device


class TestPDFProcessor:
    """PDF 处理器测试套件"""

    def test_init(self):
        """测试初始化"""
        processor = PDFProcessor()
        assert processor._p2t is None  # 未加载

    def test_lazy_loading(self):
        """测试惰性加载"""
        processor = PDFProcessor()
        # 首次访问属性时才加载
        _ = processor.p2t
        assert processor._p2t is not None

    @pytest.mark.parametrize("pdf_file", [
        "tests/fixtures/sample.pdf",
        "tests/fixtures/with_formulas.pdf"
    ])
    def test_ocr_with_pix2text(self, pdf_file):
        """测试 Pix2Text OCR 功能"""
        processor = PDFProcessor()

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        markdown = processor._ocr_with_pix2text(pdf_file)

        # 验证返回值
        assert isinstance(markdown, str)
        assert len(markdown) > 0

        # 验证 Markdown 格式（包含标题或公式）
        assert "#" in markdown or "$" in markdown

    def test_extract_images(self, tmp_path):
        """测试图像提取功能"""
        processor = PDFProcessor()
        pdf_file = "tests/fixtures/with_images.pdf"

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        images = processor._extract_images(
            pdf_file, "test_doc", str(tmp_path)
        )

        # 验证返回值
        assert isinstance(images, list)

        # 验证文件存在
        for img_name in images:
            img_path = tmp_path / "images" / "test_doc" / f"{img_name}.png"
            assert img_path.exists()

    def test_process_full(self, tmp_path):
        """测试完整处理流程"""
        processor = PDFProcessor()
        pdf_file = "tests/fixtures/sample.pdf"

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        markdown, images = processor.process(
            pdf_file, "test_doc", str(tmp_path)
        )

        # 验证返回值
        assert markdown is not None
        assert len(markdown) > 0
        assert isinstance(images, list)

        # 验证 Markdown 包含图像引用
        if images:
            assert "![img_" in markdown
            assert "/api/v1/documents/" in markdown

    def test_error_handling(self):
        """测试错误处理"""
        processor = PDFProcessor()

        with pytest.raises(ProcessingError):
            processor._ocr_with_pix2text("nonexistent.pdf")

    def test_device_detection(self):
        """测试设备检测功能"""
        device = detect_device()
        assert device in ('cuda', 'cpu'), f"无效的设备类型: {device}"

        # 如果系统有 CUDA，应该检测到
        try:
            import torch
            if torch.cuda.is_available():
                # 在自动检测模式下，应该检测到 CUDA
                # 清除环境变量以确保自动检测
                old_env = os.environ.get('PAPERREADER_DEVICE')
                if 'PAPERREADER_DEVICE' in os.environ:
                    del os.environ['PAPERREADER_DEVICE']

                device = detect_device()
                assert device == 'cuda', f"应该检测到 GPU，但得到: {device}"

                # 恢复环境变量
                if old_env:
                    os.environ['PAPERREADER_DEVICE'] = old_env
        except ImportError:
            # 如果没有 PyTorch，跳过此检查
            pass

    def test_device_parameter(self):
        """测试手动指定设备参数"""
        # 测试 CPU 模式
        processor_cpu = PDFProcessor(device='cpu')
        assert processor_cpu.device == 'cpu'

        # 测试 CUDA 模式（不实际加载模型）
        processor_cuda = PDFProcessor(device='cuda')
        assert processor_cuda.device == 'cuda'

    def test_environment_variable_control(self):
        """测试环境变量控制"""
        # 保存原始环境变量
        old_env = os.environ.get('PAPERREADER_DEVICE')

        try:
            # 测试 CPU 强制
            os.environ['PAPERREADER_DEVICE'] = 'cpu'
            device = detect_device()
            assert device == 'cpu', f"环境变量 CPU 设置失败: {device}"

            # 测试 GPU 强制
            os.environ['PAPERREADER_DEVICE'] = 'cuda'
            device = detect_device()
            assert device == 'cuda', f"环境变量 CUDA 设置失败: {device}"

            # 测试 'gpu' 别名
            os.environ['PAPERREADER_DEVICE'] = 'gpu'
            device = detect_device()
            assert device == 'cuda', f"环境变量 GPU 别名设置失败: {device}"

        finally:
            # 恢复原始环境变量
            if old_env:
                os.environ['PAPERREADER_DEVICE'] = old_env
            elif 'PAPERREADER_DEVICE' in os.environ:
                del os.environ['PAPERREADER_DEVICE']


class TestGPUFallback:
    """GPU 降级机制测试"""

    def test_cpu_initialization(self):
        """测试 CPU 模式初始化"""
        processor = PDFProcessor(device='cpu')
        assert processor.device == 'cpu'

        # 模型应该能成功加载
        _ = processor.p2t
        assert processor._p2t is not None

    @pytest.mark.skipif(
        not os.environ.get('TEST_GPU_FALLBACK'),
        reason="需要设置 TEST_GPU_FALLBACK 环境变量来测试 GPU 降级"
    )
    def test_gpu_fallback_on_error(self):
        """
        测试 GPU 初始化失败时的降级机制

        注意: 此测试需要手动触发，使用:
        TEST_GPU_FALLBACK=1 pytest tests/test_pdf_processor.py::TestGPUFallback::test_gpu_fallback_on_error
        """
        processor = PDFProcessor(device='cuda')

        # 如果系统没有 CUDA，应该在首次访问 p2t 时降级到 CPU
        try:
            _ = processor.p2t
            # 如果成功，检查设备是否降级
            try:
                import torch
                if not torch.cuda.is_available():
                    # 应该降级到 CPU
                    assert processor.device == 'cpu', "GPU 不可用时应该降级到 CPU"
            except ImportError:
                # 没有 PyTorch，应该也降级到 CPU
                assert processor.device == 'cpu'
        except Exception as e:
            # 如果降级失败，确保错误信息包含设备相关内容
            assert 'device' in str(e).lower() or 'cuda' in str(e).lower()


class TestDeviceDetectionEdgeCases:
    """设备检测边界情况测试"""

    def test_invalid_environment_variable(self):
        """测试无效的环境变量值"""
        old_env = os.environ.get('PAPERREADER_DEVICE')

        try:
            # 设置无效值
            os.environ['PAPERREADER_DEVICE'] = 'invalid_device'
            device = detect_device()
            # 应该忽略无效值并继续自动检测
            assert device in ('cuda', 'cpu')

        finally:
            if old_env:
                os.environ['PAPERREADER_DEVICE'] = old_env
            elif 'PAPERREADER_DEVICE' in os.environ:
                del os.environ['PAPERREADER_DEVICE']

    def test_case_insensitive_gpu(self):
        """测试 GPU 环境变量大小写不敏感"""
        old_env = os.environ.get('PAPERREADER_DEVICE')

        try:
            for value in ['GPU', 'Gpu', 'gpu', 'CUDA', 'Cuda', 'cuda']:
                os.environ['PAPERREADER_DEVICE'] = value
                device = detect_device()
                assert device == 'cuda', f"大小写测试失败: {value} -> {device}"

        finally:
            if old_env:
                os.environ['PAPERREADER_DEVICE'] = old_env
            elif 'PAPERREADER_DEVICE' in os.environ:
                del os.environ['PAPERREADER_DEVICE']
