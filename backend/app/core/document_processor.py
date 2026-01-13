"""
文档后台处理模块
负责协调文档处理的异步任务

职责:
- 选择合适的处理器（PDF/DOCX）
- 协调处理流程
- 错误处理和状态标记
- 结果保存
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


async def process_document_background(
    doc_id: str,
    file_path: str,
    file_type: str,
    output_base_dir: str,
    converter: str = "pix2text"
) -> None:
    """
    后台异步处理文档

    Args:
        doc_id: 文档唯一 ID
        file_path: 原始文件路径
        file_type: 文件类型（pdf/docx）
        output_base_dir: 输出基础目录
        converter: PDF转换器名称 (pix2text/marker)

    返回:
        None（结果保存到文件系统）

    状态管理:
    - 成功: 创建 {doc_id}.md 文件
    - 失败: 创建 {doc_id}.error 文件（JSON 格式）

    错误文件格式:
    {
      "error": "错误信息",
      "error_type": "错误类型",
      "timestamp": "2026-01-12T18:30:00",
      "traceback": "详细错误栈..."
    }

    设计决策:
    - 异步函数（支持 FastAPI BackgroundTasks）
    - 完全独立的错误处理（不依赖外部状态）
    - 文件系统作为状态存储（避免数据库）
    """
    from app.core.pdf_processor import PDFProcessor, ProcessingError
    import time

    md_dir = Path(output_base_dir) / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    logger.info(
        f"🚀 [BG] 开始后台处理: "
        f"doc_id={doc_id}, "
        f"file_type={file_type}, "
        f"converter={converter}"
    )

    # 系统资源监控
    try:
        import psutil
        process = psutil.Process()
        logger.info(
            f"💻 [BG] 系统资源: "
            f"cpu={process.cpu_percent()}%, "
            f"memory={process.memory_info().rss / 1024 / 1024:.1f}MB, "
            f"threads={process.num_threads()}"
        )
    except ImportError:
        logger.debug("💻 [BG] psutil未安装，跳过资源监控")

    try:
        # 步骤1：选择处理器
        logger.info(
            f"📄 [BG] 步骤1: 选择处理器 "
            f"(file_type={file_type}, converter={converter})"
        )
        if file_type.lower() == "pdf":
            processor = PDFProcessor(converter=converter)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

        # 处理器信息
        logger.debug(
            f"🔧 [BG] 处理器实例: {processor.__class__.__name__}, "
            f"converter={converter}, "
            f"device={processor.device}"
        )

        # 步骤2：处理文档
        logger.info(f"🔄 [BG] 步骤2: 开始处理文档 (doc_id={doc_id})")
        process_step_start = time.time()

        markdown_content, image_filenames = processor.process(
            file_path, doc_id, output_base_dir
        )

        processing_time = time.time() - start_time
        process_step_time = time.time() - process_step_start

        logger.info(f"⏱️ [BG] 文档处理耗时: {processing_time:.2f}秒")

        # 性能指标
        throughput = len(markdown_content) / processing_time if processing_time > 0 else 0
        logger.info(
            f"📊 [BG] 性能指标: "
            f"total_time={processing_time:.2f}s, "
            f"markdown_size={len(markdown_content)} chars, "
            f"images={len(image_filenames)}, "
            f"throughput={throughput:.0f} chars/s"
        )

        # 步骤3：保存 Markdown 文件
        logger.info(f"💾 [BG] 步骤3: 保存Markdown文件")
        save_start = time.time()

        md_path = md_dir / f"{doc_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        save_time = time.time() - save_start
        logger.info(
            f"💾 [BG] 文件保存成功: "
            f"path='{md_path}', "
            f"size={len(markdown_content)} chars, "
            f"time={save_time:.3f}s"
        )

        logger.info(
            f"✅ [BG] 文档处理成功: "
            f"doc_id={doc_id}, "
            f"markdown_size={len(markdown_content)}, "
            f"images={len(image_filenames)}, "
            f"time={processing_time:.2f}s"
        )

        # ✅ 添加处理完成摘要（独立错误处理，避免日志错误影响核心业务）
        try:
            if image_filenames:
                # 提前定义 image_dir，复用变量（DRY 原则）
                image_dir = Path(output_base_dir) / "images" / doc_id

                logger.info(f"📊 [BG] 处理完成摘要:")
                logger.info(f"   ├─ 文档ID: {doc_id}")
                logger.info(f"   ├─ Markdown大小: {len(markdown_content)} 字符")
                logger.info(f"   ├─ 图片数量: {len(image_filenames)}")
                logger.info(f"   ├─ 图片目录: {image_dir}")
                logger.info(f"   └─ 处理时间: {processing_time:.2f}秒")

                # 列出所有图片文件
                if image_dir.exists():
                    actual_images = list(image_dir.glob("img_*.png"))
                    logger.info(f"🖼️ [BG] 实际图片文件验证: {len(actual_images)} 个文件")
                    for img_path in sorted(actual_images):
                        file_size = img_path.stat().st_size
                        logger.info(f"   ├─ {img_path.name}: {file_size} 字节")
        except Exception as log_error:
            # 日志打印失败不影响处理结果
            logger.warning(f"⚠️ [BG] 摘要打印失败（不影响结果）: {log_error}")

    except Exception as e:
        # ✅ 改进：更详细的错误信息
        processing_time = time.time() - start_time
        error_path = md_dir / f"{doc_id}.error"

        # 错误时的资源状态
        try:
            import psutil
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        except:
            memory_mb = 0

        logger.error(
            f"❌ [BG] 文档处理失败: "
            f"doc_id={doc_id}, "
            f"error={str(e)}, "
            f"time={processing_time:.2f}s, "
            f"memory={memory_mb:.1f}MB",
            exc_info=True
        )

        error_info = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "doc_id": doc_id,
            "file_path": file_path,
            "file_type": file_type,
            "processing_time": f"{processing_time:.2f}s",
            "traceback": __import__('traceback').format_exc()
        }

        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)

        logger.debug(f"💾 [BG] 错误信息已保存: {error_path}")
