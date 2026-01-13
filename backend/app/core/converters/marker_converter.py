"""
Marker PDF转换器实现
高精度布局识别和表格还原
"""
import logging
import re
from typing import Tuple, List, Dict
from pathlib import Path
from .base import PDFConverterBase

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """处理错误基类"""
    pass


class MarkerConverter(PDFConverterBase):
    """
    Marker转换器

    特点:
    - 高精度布局识别(适合复杂文档)
    - 优秀的表格还原能力
    - 自动图像提取

    资源占用:
    - GPU VRAM: ~4-5GB
    - 系统RAM: ~2GB

    性能:
    - 速度: 8-15秒/页(比Pix2Text慢2-3倍)
    - 质量: 更适合复杂布局和表格密集文档
    """

    def __init__(self, device: str = "auto"):
        super().__init__(device)
        self._converter = None

    @property
    def converter(self):
        """懒加载Marker实例"""
        if self._converter is None:
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict

                logger.info(f"⏳ 正在初始化Marker模型 (device={self.device})...")

                # Marker自动检测设备,不需要手动指定
                self._converter = PdfConverter(
                    artifact_dict=create_model_dict(),
                )

                logger.info(f"✅ Marker模型初始化完成")

            except ImportError as e:
                logger.error(f"❌ Marker未安装: {e}")
                raise ImportError(
                    "marker-pdf未安装,请运行: pip install marker-pdf>=0.2.6"
                )
            except Exception as e:
                logger.error(f"❌ Marker初始化失败: {e}", exc_info=True)
                raise

        return self._converter

    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """使用Marker进行PDF转换"""
        import time

        process_start = time.time()
        pdf_name = Path(pdf_path).name
        logger.info(f"🚀 [Marker] 开始转换: doc_id={doc_id}, file='{pdf_name}'")

        try:
            # 1. 调用Marker进行转换
            convert_start = time.time()
            rendered = self.converter(pdf_path)
            convert_time = time.time() - convert_start
            logger.info(f"✅ [Marker] 转换完成: time={convert_time:.2f}s")

            # 2. 提取文本和图像
            from marker.output import text_from_rendered
            extract_start = time.time()
            markdown, _, images = text_from_rendered(rendered)
            extract_time = time.time() - extract_start

            logger.info(
                f"📝 [Marker] 内容提取: "
                f"markdown_size={len(markdown)}, "
                f"images={len(images)}, "
                f"time={extract_time:.2f}s"
            )

            # 3. 保存Marker提取的图像
            save_start = time.time()
            image_filenames, image_id_mapping = self._save_marker_images(images, doc_id, output_base_dir)
            save_time = time.time() - save_start
            logger.info(f"💾 [Marker] 图像保存: count={len(image_filenames)}, time={save_time:.2f}s")

            # 4. 处理Markdown中的图像引用(转换为API路径)
            markdown = self._process_image_references(markdown, image_filenames, image_id_mapping, doc_id)

            total_time = time.time() - process_start
            logger.info(
                f"🎉 [Marker] 转换成功: "
                f"doc_id={doc_id}, "
                f"total_time={total_time:.2f}s, "
                f"markdown_size={len(markdown)}, "
                f"images={len(image_filenames)}"
            )

            return markdown, image_filenames

        except Exception as e:
            logger.error(f"❌ [Marker] 转换失败: {e}", exc_info=True)
            raise ProcessingError(f"Marker转换失败: {str(e)}")

    def _save_marker_images(
        self,
        images: dict,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        保存Marker提取的图像

        Args:
            images: Marker返回的图像字典 {image_id: PIL.Image}
            doc_id: 文档ID
            output_base_dir: 输出目录

        Returns:
            (image_filenames, image_id_mapping)
            - image_filenames: ["img_001", "img_002", ...]
            - image_id_mapping: {"_page_0_Figure_1.jpeg": "img_001", ...}
        """
        image_dir = Path(output_base_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        image_filenames = []
        image_id_mapping = {}  # ✅ 新增：保留原始ID映射

        for idx, (original_id, img_pil) in enumerate(images.items(), 1):
            img_filename = f"img_{idx:03d}"
            img_path = image_dir / f"{img_filename}.png"

            # 保存为PNG格式
            img_pil.save(img_path, "PNG")
            image_filenames.append(img_filename)
            image_id_mapping[original_id] = img_filename  # ✅ 新增：记录映射

            # 图像保存日志
            try:
                width, height = img_pil.size
                logger.info(
                    f"🖼️ [Marker] 图像保存: "
                    f"img_{idx:03d}, "
                    f"size={width}x{height}, "
                    f"format=PNG, "
                    f"mode={img_pil.mode}"
                )
            except Exception as e:
                logger.debug(f"⚠️ [Marker] 图像元数据获取失败: {e}")

        return image_filenames, image_id_mapping  # ✅ 修改：返回两个值

    def _process_image_references(
        self,
        markdown: str,
        image_filenames: List[str],
        image_id_mapping: Dict[str, str],
        doc_id: str
    ) -> str:
        """
        处理Markdown中的图像引用

        使用原始image_id精确匹配Marker生成的引用，避免遗漏

        Args:
            markdown: 原始Markdown文本
            image_filenames: 新文件名列表 ["img_001", ...]
            image_id_mapping: 原始ID到新文件名的映射 {"_page_0_Figure_1.jpeg": "img_001", ...}
            doc_id: 文档ID
        """
        # 遍历原始image_id映射，精确替换
        for original_id, new_filename in image_id_mapping.items():
            # 生成API路径（包含完整文件名和.png扩展名）
            api_path = f"/api/v1/documents/{doc_id}/images/{new_filename}.png"

            # 替换所有可能的引用格式
            # Marker可能生成：![](original_id), ![](./original_id), 等
            patterns = [
                rf'!\[.*?\]\({re.escape(original_id)}\)',          # 精确匹配原始ID
                rf'!\[.*?\]\(\./{re.escape(original_id)}\)',       # 相对路径
                rf'!\[.*?\]\(images/{re.escape(original_id)}\)',   # images/子目录
                rf'!\[.*?\]\(\./images/{re.escape(original_id)}\)', # ./images/子目录
            ]

            for pattern in patterns:
                markdown = re.sub(pattern, f'![{new_filename}]({api_path})', markdown)

        logger.debug(
            f"🔗 [Marker] 图像引用处理完成: "
            f"count={len(image_id_mapping)}, "
            f"mapped={[f'{k}→{v}' for k, v in list(image_id_mapping.items())[:3]]}"
        )
        return markdown
