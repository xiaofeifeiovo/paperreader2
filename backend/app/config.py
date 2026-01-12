"""
配置管理模块
使用 Pydantic Settings 管理环境变量和配置
"""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""

    # API配置
    api_host: str = Field(default="127.0.0.1", description="API服务主机")
    api_port: int = Field(default=8000, description="API服务端口")
    api_prefix: str = Field(default="/api/v1", description="API前缀")

    # Qwen配置(从系统环境变量读取)
    dashscope_api_key: str = Field(default="", description="DashScope API密钥")
    qwen_api_base: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="Qwen API基础URL"
    )
    qwen_model: str = Field(default="qwen-plus", description="Qwen模型名称")

    # 存储配置
    upload_dir: Path = Field(default=Path("./data/uploads"), description="上传文件目录")
    processed_dir: Path = Field(default=Path("./data/processed"), description="处理后文件目录")

    # PDF处理选项
    use_marker: bool = Field(default=False, description="是否使用marker-pdf")

    # CORS配置
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="允许的CORS源"
    )

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别 (DEBUG/INFO/WARNING/ERROR)")
    log_file: Optional[Path] = Field(default=None, description="日志文件路径 (None=仅终端)")
    log_use_color: bool = Field(default=True, description="是否使用彩色输出")

    # 文件上传限制
    max_file_size: int = Field(default=10 * 1024 * 1024, description="最大文件大小(10MB)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
