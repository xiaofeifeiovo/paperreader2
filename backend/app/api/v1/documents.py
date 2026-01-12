"""
文档管理API路由
提供文档上传、查询、删除等功能
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict, Any
import uuid
import shutil
from datetime import datetime

from app.config import settings
from app.core.document_processor import process_document_background

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    doc_id: str
    filename: str
    status: str
    message: str
    file_size: int


class DocumentInfo(BaseModel):
    """文档信息模型"""
    doc_id: str
    filename: str
    status: str
    upload_time: float
    file_size: int


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    documents: List[DocumentInfo]


class MessageResponse(BaseModel):
    """通用消息响应模型"""
    message: str
    doc_id: str


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> DocumentUploadResponse:
    """
    上传文档并保存到本地

    支持格式: PDF, DOCX
    """
    # 1. 验证文件格式
    allowed_extensions = ['.pdf', '.docx']
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。允许的格式: {allowed_extensions}"
        )

    # 2. 验证文件大小
    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超出限制。最大允许: {settings.max_file_size / 1024 / 1024}MB"
        )

    # 3. 生成唯一文档ID
    doc_id = str(uuid.uuid4())

    # 4. 保存原始文件
    upload_dir = settings.upload_dir / doc_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"original{file_ext}"
    with open(file_path, "wb") as f:
        f.write(content)

    # 添加后台处理任务
    if background_tasks:
        background_tasks.add_task(
            process_document_background,
            doc_id=doc_id,
            file_path=str(file_path),
            file_type=file_ext[1:],  # 去掉点号，如 "pdf"
            output_base_dir=str(settings.processed_dir)
        )

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status="processing",
        message="文档正在处理中",
        file_size=file_size
    )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    获取所有文档列表
    """
    uploads_dir = settings.upload_dir

    if not uploads_dir.exists():
        return DocumentListResponse(documents=[])

    documents = []
    for doc_dir in uploads_dir.iterdir():
        if doc_dir.is_dir():
            doc_id = doc_dir.name

            # 检查处理状态
            error_file = settings.processed_dir / "markdown" / f"{doc_id}.error"
            if error_file.exists():
                status = "failed"
            else:
                md_path = settings.processed_dir / "markdown" / f"{doc_id}.md"
                if md_path.exists():
                    status = "ready"
                else:
                    status = "processing"

            # 获取原始文件信息
            original_files = list(doc_dir.glob("original.*"))
            if original_files:
                original_file = original_files[0]
                stat = original_file.stat()
                documents.append(DocumentInfo(
                    doc_id=doc_id,
                    filename=original_file.name,
                    status=status,
                    upload_time=stat.st_ctime,
                    file_size=stat.st_size
                ))

    # 按上传时间倒序排序
    documents.sort(key=lambda x: x.upload_time, reverse=True)

    return DocumentListResponse(documents=documents)


@router.get("/{doc_id}")
async def get_document(doc_id: str) -> Dict[str, Any]:
    """
    获取文档内容

    返回:
    {
      "doc_id": "abc-123",
      "content": "Markdown 内容",
      "images": ["img_001", "img_002"],
      "status": "ready"
    }

    状态处理:
    - .error 文件存在 → 返回 500 错误
    - .md 文件不存在 → 返回 404 错误
    - 正常 → 返回内容和图像列表
    """
    import json

    # 1. 检查错误文件
    error_file = settings.processed_dir / "markdown" / f"{doc_id}.error"
    if error_file.exists():
        with open(error_file, "r", encoding="utf-8") as f:
            error_info = json.load(f)
        raise HTTPException(
            status_code=500,
            detail=f"文档处理失败: {error_info.get('error', '未知错误')}"
        )

    # 2. 检查 Markdown 文件
    md_path = settings.processed_dir / "markdown" / f"{doc_id}.md"
    if not md_path.exists():
        raise HTTPException(
            status_code=404,
            detail="文档不存在或正在处理中"
        )

    # 3. 读取内容
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 4. 获取图像列表
    image_dir = settings.processed_dir / "images" / doc_id
    images = []
    if image_dir.exists():
        # 按文件名排序（img_001, img_002, ...）
        for img_path in sorted(image_dir.glob("img_*.png")):
            images.append(img_path.stem)  # 文件名不含扩展名

    return {
        "doc_id": doc_id,
        "content": content,
        "images": images,
        "status": "ready"
    }


@router.get("/{doc_id}/images/{image_name}")
async def get_image(doc_id: str, image_name: str) -> FileResponse:
    """
    获取文档中的图像
    TODO: Phase 2 - 实现图像返回
    """
    img_path = settings.processed_dir / "images" / doc_id / f"{image_name}.png"

    if not img_path.exists():
        raise HTTPException(status_code=404, detail="图像不存在")

    return FileResponse(img_path, media_type="image/png")


@router.delete("/{doc_id}", response_model=MessageResponse)
async def delete_document(doc_id: str) -> MessageResponse:
    """
    删除文档及其所有相关文件
    """
    # 删除上传文件
    upload_dir = settings.upload_dir / doc_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    # 删除Markdown文件
    md_path = settings.processed_dir / "markdown" / f"{doc_id}.md"
    if md_path.exists():
        md_path.unlink()

    # 删除图像目录
    image_dir = settings.processed_dir / "images" / doc_id
    if image_dir.exists():
        shutil.rmtree(image_dir)

    return MessageResponse(message="文档已删除", doc_id=doc_id)
