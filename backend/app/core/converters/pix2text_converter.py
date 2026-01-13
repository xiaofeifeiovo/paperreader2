"""
Pix2Text PDF转换器实现
从现有pdf_processor.py迁移代码,保持功能完全一致
"""
import logging
from typing import Tuple, List
from pathlib import Path
import fitz  # PyMuPDF
from .base import PDFConverterBase

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """处理错误基类"""
    pass


class Pix2TextConverter(PDFConverterBase):
    """
    Pix2Text转换器

    特点:
    - 快速OCR识别(3-5秒/页)
    - 优秀的公式识别能力
    - 适合学术论文和技术文档

    资源占用:
    - GPU VRAM: ~500MB
    - 系统RAM: ~1GB
    """

    def __init__(self, device: str = "auto"):
        super().__init__(device)
        self._p2t = None

    @property
    def p2t(self):
        """懒加载Pix2Text实例(复用现有逻辑)"""
        if self._p2t is None:
            from pix2text import Pix2Text
            logger.info(f"⏳ 正在初始化Pix2Text模型 (device={self.device})...")

            try:
                self._p2t = Pix2Text.from_config(
                    enable_formula=True,
                    enable_table=True,
                    device=self.device
                )
                logger.info(f"✅ Pix2Text模型初始化完成")

            except ValueError as e:
                if 'CUDAExecutionProvider' in str(e) and self.device == 'cuda':
                    logger.warning(f"🔄 GPU初始化失败,降级到CPU...")
                    self.device = 'cpu'
                    self._p2t = Pix2Text.from_config(
                        enable_formula=True,
                        enable_table=True,
                        device='cpu'
                    )
                else:
                    raise ProcessingError(f"Pix2Text初始化失败: {e}")

        return self._p2t

    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """使用Pix2Text进行PDF转换(完全迁移现有逻辑)"""
        import time
        from pathlib import Path

        process_start = time.time()
        logger.info(f"🚀 [Pix2Text] 开始转换: doc_id={doc_id}")

        # 1. OCR识别(迁移现有代码)
        ocr_start = time.time()
        markdown = self._ocr_with_pix2text(pdf_path)
        ocr_time = time.time() - ocr_start
        logger.info(f"✅ [Pix2Text] OCR完成: time={ocr_time:.2f}s")

        # 2. 提取图像(迁移现有代码)
        extract_start = time.time()
        image_filenames = self._extract_images(pdf_path, doc_id, output_base_dir)
        extract_time = time.time() - extract_start
        logger.info(f"✅ [Pix2Text] 图像提取: count={len(image_filenames)}, time={extract_time:.2f}s")

        # 3. 插入图像引用(迁移现有代码)
        final_markdown = self._insert_image_references(markdown, image_filenames, doc_id)

        total_time = time.time() - process_start
        logger.info(f"🎉 [Pix2Text] 转换完成: time={total_time:.2f}s")

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
        import time
        from pathlib import Path

        try:
            ocr_start = time.time()
            pdf_name = Path(pdf_path).name
            logger.info(f"🔍 [Pix2Text] OCR识别开始: pdf='{pdf_name}'")

            # 调用 recognize_pdf 获取 Document 对象
            result = self.p2t.recognize_pdf(
                pdf_path,
                return_text=False  # 返回 Document 对象(包含更多元数据)
            )

            ocr_time = time.time() - ocr_start
            page_count = len(result.pages)
            avg_time_per_page = ocr_time / page_count if page_count > 0 else 0

            logger.info(
                f"📝 [Pix2Text] 页面识别完成: "
                f"page_count={page_count}, "
                f"time={ocr_time:.2f}s, "
                f"avg={avg_time_per_page:.2f}s/页"
            )
            logger.debug(f"📊 [Pix2Text] 文档统计: total_pages={page_count}, has_text=True")

            # 使用 to_markdown() 方法获取真正的 Markdown 文本
            import tempfile
            markdown_gen_start = time.time()
            with tempfile.TemporaryDirectory() as temp_dir:
                markdown_content = result.to_markdown(
                    out_dir=temp_dir,
                    root_url=None,  # 不使用 Pix2Text 的图片引用,我们手动处理
                    markdown_fn=None  # 不保存到文件,直接返回字符串
                )

            markdown_gen_time = time.time() - markdown_gen_start
            line_count = len(markdown_content.splitlines())

            logger.info(
                f"✍️ [Pix2Text] Markdown生成完成: "
                f"length={len(markdown_content)}, "
                f"lines={line_count}, "
                f"time={markdown_gen_time:.2f}s"
            )
            logger.debug(f"🔍 [Pix2Text] Markdown预览: {markdown_content[:200]}...")

            return markdown_content

        except Exception as e:
            logger.error(f"❌ [Pix2Text] OCR识别失败: {e}", exc_info=True)
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
            图像文件名列表(不含路径和扩展名)

        设计决策:
        - 去重: 使用 seen_xrefs 避免重复提取相同图像
        - 命名: 固定格式 img_001.png, img_002.png
        - 保存: PNG 格式(通用性好)
        - 质量: 保持原始质量,不压缩
        - 回退: 如果没有提取到图像,记录警告但不报错

        Raises:
            ProcessingError: 图像提取失败时抛出
        """
        import time
        from pathlib import Path

        image_dir = Path(output_base_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        try:
            extract_start = time.time()
            doc = fitz.open(pdf_path)
            pdf_name = Path(pdf_path).name

            logger.info(f"📖 [Pix2Text] 打开PDF文件: pages={len(doc)}, path='{pdf_name}'")

            image_filenames = []
            seen_xrefs = set()  # 去重
            img_index = 1
            total_image_bytes = 0

            logger.info(f"🔍 [Pix2Text] 开始扫描图像: total_pages={len(doc)}")

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                # 页面级日志(DEBUG)
                logger.debug(f"📄 [Pix2Text] 页面 {page_num + 1}/{len(doc)}: 发现 {len(image_list)} 个图像对象")

                for img_in_page_idx, img in enumerate(image_list):
                    xref = img[0]  # 图像交叉引用号

                    # 跳过重复图像
                    if xref in seen_xrefs:
                        logger.debug(f"⏭️ [Pix2Text] 跳过重复图像: xref={xref}")
                        continue
                    seen_xrefs.add(xref)

                    # 提取图像
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # 使用PIL获取图像元数据
                        try:
                            import io
                            from PIL import Image
                            img_pil = Image.open(io.BytesIO(image_bytes))
                            width, height = img_pil.size
                            format_name = img_pil.format
                            mode = img_pil.mode
                        except Exception as pil_error:
                            # PIL解析失败,使用基本信息
                            logger.debug(f"⚠️ [Pix2Text] PIL解析失败,使用基本信息: {pil_error}")
                            width, height = base_image.get("width", 0), base_image.get("height", 0)
                            format_name = image_ext.upper()
                            mode = "unknown"

                        # 生成文件名(固定格式)
                        img_filename = f"img_{img_index:03d}"
                        img_path = image_dir / f"{img_filename}.png"

                        # 保存图像
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)

                        total_image_bytes += len(image_bytes)

                        # 图像提取成功日志(INFO)
                        logger.info(
                            f"🖼️ [Pix2Text] 图像提取成功: "
                            f"img_{img_index:03d}, "
                            f"xref={xref}, "
                            f"size={width}x{height}, "
                            f"format={format_name}, "
                            f"mode={mode}, "
                            f"bytes={len(image_bytes)}, "
                            f"page={page_num + 1}"
                        )

                        # DEBUG级别:更多技术细节
                        logger.debug(
                            f"🔍 [Pix2Text] 图像技术细节: "
                            f"img_{img_index:03d}, "
                            f"ext={image_ext}, "
                            f"filename={img_filename}.png"
                        )

                        image_filenames.append(img_filename)
                        img_index += 1

                    except Exception as e:
                        logger.warning(
                            f"⚠️ [Pix2Text] 图像提取失败: "
                            f"xref={xref}, "
                            f"page={page_num + 1}, "
                            f"error={str(e)}"
                        )
                        continue

            # 保存文档信息(必须在关闭前)
            page_count = len(doc)

            doc.close()
            extract_time = time.time() - extract_start

            # 提取总结
            if not image_filenames:
                logger.warning(
                    f"⚠️ [Pix2Text] 未提取到图像: "
                    f"doc_id={doc_id}, "
                    f"time={extract_time:.2f}s"
                )
            else:
                # 使用保存的页数
                avg_time_per_page = extract_time / page_count if page_count > 0 else 0
                logger.info(
                    f"✅ [Pix2Text] 图像提取完成: "
                    f"count={len(image_filenames)}, "
                    f"time={extract_time:.2f}s, "
                    f"avg={avg_time_per_page:.2f}s/页, "
                    f"total_bytes={total_image_bytes}"
                )

                # ✅ 验证所有图片文件是否真实存在
                if image_filenames:
                    missing_images = []
                    for img_name in image_filenames:
                        img_path = image_dir / f"{img_name}.png"
                        if not img_path.exists():
                            missing_images.append(img_name)
                            logger.error(f"❌ [Pix2Text] 图片文件验证失败: {img_path} 不存在")

                    if missing_images:
                        logger.error(
                            f"❌ [Pix2Text] 图片验证失败: "
                            f"缺失 {len(missing_images)}/{len(image_filenames)} 个图片"
                        )
                        logger.error(f"   缺失列表: {missing_images}")
                    else:
                        logger.info(
                            f"✅ [Pix2Text] 图片验证通过: "
                            f"所有 {len(image_filenames)} 个图片文件存在"
                        )

            return image_filenames

        except Exception as e:
            logger.error(f"❌ [Pix2Text] 图像提取失败: {e}", exc_info=True)
            # 图像提取失败不阻断整个处理流程
            logger.warning("⚠️ [Pix2Text] 继续处理流程,不包含图像")
            return []

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

        设计决策(MVP 阶段):
        - 简单策略: 在文档末尾添加所有图像
        - 图像引用格式: ![img_name](/api/v1/documents/{doc_id}/images/img_name)
        - 未来改进: 智能匹配插入位置(基于文本相似度)

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
            # 生成 API 路径(前端可直接访问)
            # 修复: 添加.png扩展名，确保URL完整可访问
            api_path = f"/api/v1/documents/{doc_id}/images/{img_name}.png"
            images_section += f"**图 {i}**: ![{img_name}]({api_path})\n\n"

        return markdown + images_section
