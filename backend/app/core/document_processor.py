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
    output_base_dir: str
) -> None:
    """
    后台异步处理文档

    Args:
        doc_id: 文档唯一 ID
        file_path: 原始文件路径
        file_type: 文件类型（pdf/docx）
        output_base_dir: 输出基础目录

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

    md_dir = Path(output_base_dir) / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"开始后台处理: doc_id={doc_id}, file_type={file_type}")

    try:
        # 1. 选择处理器（根据文件类型）
        if file_type.lower() == "pdf":
            processor = PDFProcessor()
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

        # 2. 处理文档
        markdown_content, image_filenames = processor.process(
            file_path, doc_id, output_base_dir
        )

        # 3. 保存 Markdown 文件
        md_path = md_dir / f"{doc_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(
            f"✅ 文档处理成功: doc_id={doc_id}, "
            f"markdown_size={len(markdown_content)}, images={len(image_filenames)}"
        )

    except Exception as e:
        # 4. 错误处理：创建错误文件
        error_path = md_dir / f"{doc_id}.error"
        error_info = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "doc_id": doc_id,
            "file_path": file_path,
            "traceback": __import__('traceback').format_exc()
        }

        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)

        logger.error(
            f"❌ 文档处理失败: doc_id={doc_id}, error={str(e)}",
            exc_info=True
        )
