"""
PDF转换器抽象基类
定义统一的转换器接口,确保所有转换器实现具有相同的签名和行为
"""
from abc import ABC, abstractmethod
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class PDFConverterBase(ABC):
    """
    PDF转换器抽象基类

    所有PDF转换器必须实现此接口,确保:
    1. 统一的输入输出格式
    2. 一致的错误处理方式
    3. 兼容的图像引用格式
    """

    def __init__(self, device: str = "auto"):
        """
        初始化转换器

        Args:
            device: 设备类型 ('cuda', 'cpu', 'auto')
        """
        self.device = device
        logger.info(f"📦 初始化转换器: {self.__class__.__name__}, device={device}")

    @abstractmethod
    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        将PDF转换为Markdown

        Args:
            pdf_path: PDF文件绝对路径
            doc_id: 文档唯一ID
            output_base_dir: 输出基础目录(通常是 data/processed)

        Returns:
            (markdown_content, image_filenames)
            - markdown_content: 完整的Markdown文本
            - image_filenames: 图像文件名列表(不含路径和扩展名)

        Raises:
            ProcessingError: 转换失败时抛出

        注意:
            - 图像应保存到 {output_base_dir}/images/{doc_id}/
            - 图像命名格式: img_001.png, img_002.png, ...
            - Markdown中的图像引用应使用API路径格式
        """
        pass

    def get_converter_name(self) -> str:
        """获取转换器名称"""
        return self.__class__.__name__
