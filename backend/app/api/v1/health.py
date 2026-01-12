"""
健康检查API路由
提供系统健康状态检查接口
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import sys
from pathlib import Path

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    python_version: str
    components: Dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    健康检查端点

    返回系统状态和组件信息
    """
    # 检查关键目录是否存在
    upload_dir = Path("./data/uploads")
    processed_dir = Path("./data/processed")

    components = {
        "upload_dir": "ready" if upload_dir.exists() else "not_found",
        "processed_dir": "ready" if processed_dir.exists() else "not_found",
    }

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        python_version=sys.version,
        components=components
    )


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """
    简单的ping端点,用于快速检查服务是否运行
    """
    return {"status": "pong", "service": "paperreader2-backend"}
