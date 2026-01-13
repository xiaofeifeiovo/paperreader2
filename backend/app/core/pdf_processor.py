"""
PDF处理器 - 门面类(Facade Pattern)
根据converter参数动态选择具体转换器实现
"""
from typing import Tuple, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """
    智能检测最佳设备

    检测顺序:
    1. 环境变量 PAPERREADER_DEVICE(手动强制)
    2. PyTorch CUDA 可用性 → 'cuda'
    3. 降级到 'cpu'

    Returns:
        'cuda' 或 'cpu'
    """
    import os

    # 1. 检查环境变量(最高优先级)
    force_device = os.environ.get('PAPERREADER_DEVICE', '').lower()
    if force_device in ('cuda', 'gpu', 'cpu'):
        logger.info(f"🎯 使用环境变量强制设备: {force_device}")
        return force_device if force_device != 'gpu' else 'cuda'

    # 2. 检查 CUDA 可用性
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("🚀 检测到 CUDA,将使用 GPU 加速")
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return 'cuda'
    except Exception as e:
        logger.warning(f"⚠️  检测 CUDA 失败: {e}")

    # 3. 降级到 CPU
    logger.info("💻 将使用 CPU 进行处理")
    return 'cpu'


class ProcessingError(Exception):
    """文档处理错误基类"""
    pass


class PDFProcessor:
    """
    PDF处理器门面类

    职责:
    - 根据converter参数选择具体转换器
    - 提供统一的处理接口
    - 确保懒加载隔离,避免同时加载多个转换器

    设计模式:
    - 门面模式(Facade):隐藏转换器实现细节
    - 策略模式(Strategy):动态选择转换器算法
    """

    # 转换器映射表
    CONVERTERS = {
        "pix2text": "app.core.converters.pix2text_converter",
        "marker": "app.core.converters.marker_converter",
    }

    def __init__(self, converter: str = "pix2text", device: Optional[str] = None):
        """
        初始化处理器

        Args:
            converter: 转换器名称 ("pix2text" 或 "marker")
            device: 设备类型 ("cuda", "cpu", "auto"),None表示自动检测

        Raises:
            ValueError: 不支持的转换器
        """
        self.converter_name = converter
        self.device = device or detect_device()
        self._converter_impl = None  # 延迟加载,避免同时初始化

        logger.info(
            f"📦 PDFProcessor初始化: "
            f"converter={converter}, "
            f"device={self.device}"
        )

    @property
    def converter_impl(self):
        """
        懒加载转换器实现

        延迟加载的好处:
        1. 避免启动时同时加载多个模型(节省内存)
        2. 只加载用户选择的转换器
        3. 加快启动速度
        """
        if self._converter_impl is None:
            self._converter_impl = self._load_converter(self.converter_name)
        return self._converter_impl

    def _load_converter(self, converter_name: str):
        """
        动态加载转换器类

        Args:
            converter_name: 转换器名称

        Returns:
            转换器实例

        Raises:
            ValueError: 不支持的转换器
            ImportError: 转换器依赖未安装
        """
        if converter_name not in self.CONVERTERS:
            raise ValueError(
                f"❌ 不支持的转换器: {converter_name}. "
                f"支持的转换器: {list(self.CONVERTERS.keys())}"
            )

        # 动态导入转换器模块
        module_path = self.CONVERTERS[converter_name]
        try:
            module = __import__(module_path, fromlist=[""])

            # 获取转换器类名(如 Pix2TextConverter)
            class_name = converter_name.title().replace("_", "") + "Converter"
            converter_class = getattr(module, class_name)

            # 实例化转换器
            instance = converter_class(device=self.device)

            logger.info(f"✅ 转换器加载成功: {class_name}")
            return instance

        except ImportError as e:
            # 优雅降级:如果marker未安装,降级到pix2text
            if converter_name == "marker":
                logger.warning(
                    f"⚠️ marker-pdf未安装,自动降级到pix2text。"
                    f"安装命令: pip install marker-pdf>=0.2.6"
                )
                logger.warning(f"   详细错误: {e}")
                # 递归加载pix2text
                return self._load_converter("pix2text")
            else:
                logger.error(f"❌ 转换器加载失败: {e}", exc_info=True)
                raise ProcessingError(
                    f"转换器 {converter_name} 加载失败: {str(e)}"
                )

    def process(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        处理PDF文档

        Args:
            pdf_path: PDF文件绝对路径
            doc_id: 文档唯一ID
            output_base_dir: 输出基础目录

        Returns:
            (markdown_content, image_filenames)
        """
        logger.info(
            f"🚀 [PDF] 使用 {self.converter_name} 转换器处理PDF: "
            f"doc_id={doc_id}"
        )

        return self.converter_impl.convert_to_markdown(
            pdf_path, doc_id, output_base_dir
        )
