"""
PDF 文档处理器
使用 Pix2Text 进行 OCR 识别，PyMuPDF 提取图像

职责:
- PDF OCR 识别（文本 + 公式）
- 图像提取和保存
- Markdown 生成和图像引用插入
"""
import os
from typing import Tuple, List, Optional
from pathlib import Path
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """
    智能检测最佳设备

    检测顺序:
    1. 环境变量 PAPERREADER_DEVICE（手动强制）
    2. PyTorch CUDA 可用性 → 'cuda'
    3. 降级到 'cpu'

    Returns:
        'cuda' 或 'cpu'
    """
    # 1. 检查环境变量（最高优先级）
    force_device = os.environ.get('PAPERREADER_DEVICE', '').lower()
    if force_device in ('cuda', 'gpu', 'cpu'):
        logger.info(f"🎯 使用环境变量强制设备: {force_device}")
        return force_device if force_device != 'gpu' else 'cuda'

    # 2. 检查 CUDA 可用性
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("🚀 检测到 CUDA，将使用 GPU 加速")
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
    """PDF 处理器 - Pix2Text + PyMuPDF（支持 GPU 加速）"""

    def __init__(self, device: Optional[str] = None):
        """
        初始化处理器

        Args:
            device: 可选，指定设备 ('cuda' 或 'cpu')。
                    None 表示自动检测。

        设计决策:
        - 延迟加载 Pix2Text，避免启动时加载模型（启动时间过长）
        - 使用 @property 惰性初始化
        - 支持自动设备检测
        """
        self._p2t = None
        # 如果未指定设备，则自动检测
        self.device = device if device is not None else detect_device()
        logger.info(f"📦 PDFProcessor 初始化，设备: {self.device}")

    @property
    def p2t(self):
        """懒加载 Pix2Text 实例"""
        if self._p2t is None:
            from pix2text import Pix2Text
            logger.info(f"⏳ 正在初始化 Pix2Text 模型 (device={self.device})...")

            try:
                self._p2t = Pix2Text.from_config(
                    enable_formula=True,  # 启用公式识别
                    enable_table=True,    # 启用表格识别
                    device=self.device     # 使用检测到的设备
                )
                logger.info("✅ Pix2Text 模型初始化完成")
            except Exception as e:
                logger.error(f"❌ Pix2Text 初始化失败 (device={self.device}): {e}")
                # 如果 GPU 初始化失败，尝试降级到 CPU
                if self.device == 'cuda':
                    logger.warning("🔄 GPU 初始化失败，尝试降级到 CPU...")
                    self.device = 'cpu'
                    self._p2t = Pix2Text.from_config(device='cpu')
                    logger.info("✅ Pix2Text 模型初始化完成（CPU 模式）")
                else:
                    raise

        return self._p2t

    def process(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        处理 PDF 文档（主入口）

        Args:
            pdf_path: PDF 文件绝对路径
            doc_id: 文档唯一 ID
            output_base_dir: 输出基础目录（通常是 data/processed）

        Returns:
            (markdown_content, image_filenames)
            - markdown_content: 完整的 Markdown 文本
            - image_filenames: 图像文件名列表（不含路径和扩展名）

        Raises:
            ProcessingError: 处理失败时抛出

        流程:
        1. OCR 识别 → Markdown 文本
        2. 图像提取 → 图像文件列表
        3. 插入引用 → 最终 Markdown
        """
        logger.info(f"开始处理 PDF: {pdf_path}, doc_id: {doc_id}")

        # 1. OCR 识别
        markdown = self._ocr_with_pix2text(pdf_path)
        logger.info(f"OCR 识别完成，文本长度: {len(markdown)}")

        # 2. 提取图像
        image_filenames = self._extract_images(pdf_path, doc_id, output_base_dir)
        logger.info(f"图像提取完成，共 {len(image_filenames)} 张")

        # 3. 插入图像引用
        final_markdown = self._insert_image_references(markdown, image_filenames, doc_id)

        logger.info(f"PDF 处理完成: {doc_id}")
        return final_markdown, image_filenames

    def _ocr_with_pix2text(self, pdf_path: str) -> str:
        """
        使用 Pix2Text 进行 OCR 识别

        Args:
            pdf_path: PDF 文件路径

        Returns:
            Markdown 格式文本

        技术细节:
        - Pix2Text 默认启用公式识别 (formula_ocr=True)
        - 输出格式: Markdown (标题、段落、列表、表格)
        - 公式格式: LaTeX (行内 $...$, 行间 $$...$$)

        Raises:
            ProcessingError: OCR 失败时抛出
        """
        try:
            logger.info(f"Pix2Text 识别: {pdf_path}")
            result = self.p2t.recognize_pdf(
                pdf_path,
                return_text=False  # 返回 Document 对象
            )
            # 从 Document 对象获取 markdown 文本
            markdown_content = result.__str__()
            return markdown_content

        except Exception as e:
            logger.error(f"Pix2Text 识别失败: {e}", exc_info=True)
            raise ProcessingError(f"OCR 识别失败: {str(e)}")

    def _extract_images(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> List[str]:
        """
        使用 PyMuPDF 提取图像

        Args:
            pdf_path: PDF 文件路径
            doc_id: 文档 ID
            output_base_dir: 输出基础目录

        Returns:
            图像文件名列表（不含路径和扩展名）

        设计决策:
        - 去重: 使用 seen_xrefs 避免重复提取相同图像
        - 命名: 固定格式 img_001.png, img_002.png
        - 保存: PNG 格式（通用性好）
        - 质量: 保持原始质量，不压缩

        Raises:
            ProcessingError: 图像提取失败时抛出
        """
        image_dir = Path(output_base_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        try:
            doc = fitz.open(pdf_path)
            image_filenames = []
            seen_xrefs = set()  # 去重
            img_index = 1

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img in image_list:
                    xref = img[0]  # 图像交叉引用号

                    # 跳过重复图像
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    # 提取图像
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 生成文件名（固定格式）
                    img_filename = f"img_{img_index:03d}"
                    img_path = image_dir / f"{img_filename}.png"

                    # 保存图像
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    image_filenames.append(img_filename)
                    img_index += 1

            doc.close()
            logger.info(f"成功提取 {len(image_filenames)} 张图像")
            return image_filenames

        except Exception as e:
            logger.error(f"图像提取失败: {e}", exc_info=True)
            raise ProcessingError(f"图像提取失败: {str(e)}")

    def _insert_image_references(
        self,
        markdown: str,
        image_filenames: List[str],
        doc_id: str
    ) -> str:
        """
        在 Markdown 中插入图像引用

        Args:
            markdown: 原始 Markdown 文本
            image_filenames: 图像文件名列表
            doc_id: 文档 ID

        Returns:
            包含图像引用的 Markdown

        设计决策（MVP 阶段）:
        - 简单策略: 在文档末尾添加所有图像
        - 图像引用格式: ![img_name](/api/v1/documents/{doc_id}/images/img_name)
        - 未来改进: 智能匹配插入位置（基于文本相似度）

        示例输出:
        ```markdown
        ...原有内容...

        ## 文档图像

        **图 1**: ![img_001](/api/v1/documents/{doc_id}/images/img_001)

        **图 2**: ![img_002](/api/v1/documents/{doc_id}/images/img_002)
        ```
        """
        if not image_filenames:
            return markdown

        # 在文档末尾添加图像章节
        images_section = "\n\n## 文档图像\n\n"

        for i, img_name in enumerate(image_filenames, 1):
            # 生成 API 路径（前端可直接访问）
            api_path = f"/api/v1/documents/{doc_id}/images/{img_name}"
            images_section += f"**图 {i}**: ![{img_name}]({api_path})\n\n"

        return markdown + images_section
