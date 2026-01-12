"""
FastAPI应用入口
PaperReader2 后端服务主程序
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.v1 import health, documents
from app.utils.logging_config import setup_logging


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 初始化日志系统
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,
        use_color=settings.log_use_color
    )

    # 启动时执行
    logger.info(f"🚀 PaperReader2 Backend Starting...")
    logger.info(f"📁 Upload Directory: {settings.upload_dir}")
    logger.info(f"📁 Processed Directory: {settings.processed_dir}")
    logger.info(f"🔧 Log Level: {settings.log_level}")
    logger.info(f"📄 Log File: {settings.log_file or '仅终端输出'}")

    # 确保必要的目录存在
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    yield

    # 关闭时执行
    logger.info("🛑 PaperReader2 Backend Shutting down...")


# 创建FastAPI应用实例
app = FastAPI(
    title="PaperReader2 API",
    description="AI融合论文辅助阅读器 - 后端API服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(
    health.router,
    prefix=settings.api_prefix,
    tags=["health"]
)

app.include_router(
    documents.router,
    prefix=settings.api_prefix,
    tags=["documents"]
)


# 根路径
@app.get("/")
async def root():
    """
    根路径,返回API基本信息
    """
    return {
        "name": "PaperReader2 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "health": f"{settings.api_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn

    print("""
    ╔════════════════════════════════════════╗
    ║   PaperReader2 Backend Service         ║
    ║   AI-Powered Paper Reader              ║
    ╚════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
