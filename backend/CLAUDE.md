# PaperReader2 Backend

> [根目录](../CLAUDE.md) > **backend**

## 模块职责

后端模块是 PaperReader2 的核心服务层，负责：

- RESTful API 服务（FastAPI）
- 文档上传和存储管理
- PDF/DOCX 转 Markdown 处理（Pix2Text + PyMuPDF）
- AI 问答服务（Qwen API 集成）
- 上下文管理和 Token 计数

## 入口和启动

### 主入口

- **文件**: `app/main.py`
- **应用**: FastAPI 实例
- **启动命令**:
  ```bash
  python -m app.main
  # 或
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```

### 启动流程

1. 加载配置 (`app/config.py`)
2. 创建 FastAPI 应用实例
3. 配置 CORS 中间件
4. 注册 API 路由
5. 创建必要的目录 (`data/uploads/`, `data/processed/`)

### 应用生命周期

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    - 打印配置信息
    - 创建必要目录
    yield
    # 关闭时
    - 清理资源
```

## 外部接口

### API 端点

#### 健康检查 (`app/api/v1/health.py`)

- `GET /api/v1/health` - 系统健康状态
- `GET /api/v1/health/ping` - 快速 ping

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "python_version": "3.11.x",
  "components": {
    "upload_dir": "ready",
    "processed_dir": "ready"
  }
}
```

#### 文档管理 (`app/api/v1/documents.py`)

- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/list` - 获取文档列表
- `GET /api/v1/documents/{doc_id}` - 获取文档内容
- `GET /api/v1/documents/{doc_id}/images/{image_name}` - 获取图像
- `DELETE /api/v1/documents/{doc_id}` - 删除文档

**上传响应示例**:
```json
{
  "doc_id": "uuid-string",
  "filename": "paper.pdf",
  "status": "uploaded",
  "message": "文档上传成功,等待处理",
  "file_size": 1234567
}
```

#### AI 问答 (`app/api/v1/chat.py`) - Phase 3

- `POST /api/v1/chat/message` - 流式聊天 (SSE)

### API 文档

- Swagger UI: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/api/openapi.json`

## 关键依赖和配置

### 核心依赖

```
fastapi==0.109.0          # Web 框架
uvicorn[standard]==0.27.0 # ASGI 服务器
pix2text>=1.1.0           # PDF OCR + 公式识别
pymupdf==1.23.8           # PDF 图像提取
python-docx==1.1.0        # DOCX 处理 (Phase 3)
dashscope>=1.14.0         # Qwen API SDK (Phase 3)
tiktoken>=0.5.0           # Token 计数 (Phase 3)
pydantic>=2.9.2,<3.0.0    # 数据验证
pydantic-settings==2.1.0  # 配置管理
```

### 配置管理 (`app/config.py`)

使用 Pydantic Settings 管理环境变量：

```python
class Settings(BaseSettings):
    # API 配置
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Qwen 配置
    dashscope_api_key: str
    qwen_model: str = "qwen-plus"

    # 存储配置
    upload_dir: Path = Path("./data/uploads")
    processed_dir: Path = Path("./data/processed")

    # CORS 配置
    cors_origins: List[str] = ["http://localhost:5173"]
```

### 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
API_HOST=127.0.0.1
API_PORT=8000
QWEN_MODEL=qwen-plus
USE_MARKER=false
```

## 数据模型

### Pydantic 模型 (`app/models/`)

#### 文档相关

```python
class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    message: str
    file_size: int

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    status: str  # uploaded, processing, ready, error
    upload_time: float
    file_size: int
```

#### 聊天相关 (Phase 3)

```python
class ChatRequest(BaseModel):
    doc_id: str
    question: str
    history: List[Dict[str, str]] = []
```

## 存储结构

### 目录布局

```
data/
├── uploads/                      # 原始上传文件
│   └── {doc_id}/
│       └── original.{pdf|docx}
│
└── processed/                    # 处理后文件
    ├── markdown/                 # Markdown 文件
    │   └── {doc_id}.md
    └── images/                   # 提取的图像
        └── {doc_id}/
            ├── img_001.png
            ├── img_002.png
            └── ...
```

### 文件命名约定

- **原始文件**: `original.{ext}` (PDF 或 DOCX)
- **Markdown 文件**: `{doc_id}.md`
- **图像文件**: `img_{index:03d}.png`

## 核心业务逻辑

### Phase 2: 文档处理 (已完成 ✅)

#### PDFProcessor (`app/core/pdf_processor.py`)

**职责**: 使用 Pix2Text 进行 OCR 识别和公式提取

**关键特性**:
- **GPU自动检测**: `detect_device()` 函数实现多层检测
  - 环境变量 `PAPERREADER_DEVICE` 强制指定 (cuda/cpu/auto)
  - 自动检测CUDA可用性
  - 降级到CPU模式

- **懒加载模式**: `@property` 装饰器延迟加载Pix2Text模型
  - 避免启动时下载模型(1-2分钟)
  - 首次使用时才初始化

- **优雅降级**: GPU初始化失败自动切换CPU

**流程**:
```
1. Pix2Text.recognize_pdf()
   - OCR 文本识别
   - 数学公式转 LaTeX
   - 输出 Markdown 格式

2. PyMuPDF 提取图像
   - 高质量图像提取
   - 保存到 processed/images/{doc_id}/

3. 合成 Markdown
   - 插入图像引用
   - 生成最终 Markdown
```

**接口**:
```python
class PDFProcessor:
    def __init__(self, device: Optional[str] = None):
        """device: 'cuda' 或 'cpu', None表示自动检测"""

    @property
    def p2t(self):
        """懒加载Pix2Text实例"""

    def process(self, pdf_path: str, doc_id: str, output_dir: str) -> Tuple[str, List[str]]:
        """返回 (markdown_content, image_paths)"""
```

#### 错误处理机制 (`app/core/document_processor.py`)

**职责**: 协调文档处理和错误隔离

**关键特性**:
- **错误文件格式**: JSON格式的`.error`文件
  ```json
  {
    "error": "错误信息",
    "error_type": "错误类型",
    "timestamp": "2026-01-12T18:30:00",
    "doc_id": "文档ID",
    "file_path": "文件路径",
    "traceback": "详细错误栈..."
  }
  ```

- **状态管理**: 通过文件系统推断状态
  - `{doc_id}.md` 存在 → ready
  - `{doc_id}.error` 存在 → error
  - 都不存在 → processing

#### DOCXProcessor (`app/core/docx_processor.py`) - 未实现

**职责**: 处理 Word 文档

**流程**:
```
1. python-docx 提取段落和样式
2. 提取嵌入图像
3. MathML 公式转 LaTeX
4. 生成 Markdown
```

### Phase 3: AI 问答功能 (计划中 📋)

> 🚧 以下模块尚未实现,设计仅供参考

#### ContextBuilder (`app/core/context_builder.py`) - 未实现

**职责**: 构建问答上下文

**流程**:
```
1. 读取 Markdown 文档
2. 使用 tiktoken 统计 Token
3. 智能截断策略:
   - 优先: 摘要、引言、结论
   - 其次: 方法、实验、结果
   - 最后: 参考文献
4. 添加对话历史（最近 10 轮）
5. 构建完整 Prompt
```

**接口**:
```python
class ContextBuilder:
    def build_context(
        self,
        doc_id: str,
        question: str,
        chat_history: List[Dict],
        markdown_dir: str
    ) -> str:
        """返回完整 Prompt"""
```

#### LLMService (`app/core/llm_service.py`) - 未实现

**职责**: 调用 Qwen API

**流程**:
```
1. 配置 API 密钥
2. 调用 DashScope SDK
3. 流式响应处理
4. 错误重试
```

**接口**:
```python
class LLMService:
    async def stream_chat(self, prompt: str, max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        """流式调用 Qwen API"""
```

## 测试

### 运行测试

```bash
# 所有测试
pytest

# 特定测试
pytest tests/test_pdf_processor.py

# 覆盖率
pytest --cov=app --cov-report=html
```

### 测试结构 (计划)

```
tests/
├── __init__.py
├── test_api.py                  # API 测试
├── test_pdf_processor.py        # PDF 处理测试
├── test_docx_processor.py       # DOCX 处理测试 (Phase 3)
├── test_context_builder.py      # 上下文构建测试 (Phase 3)
└── test_llm_service.py          # LLM 服务测试 (Phase 3)
```

### 测试示例

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_document():
    with open("test.pdf", "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    assert "doc_id" in response.json()
```

## 开发指南

### 添加新 API 端点

1. 在 `app/api/v1/` 创建路由文件
2. 定义 Pydantic 模型（请求/响应）
3. 实现路由处理函数
4. 在 `app/main.py` 注册路由

**示例**:
```python
# app/api/v1/example.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/example", tags=["example"])

class ExampleRequest(BaseModel):
    name: str

@router.post("/")
async def create_example(request: ExampleRequest):
    return {"message": f"Hello {request.name}"}
```

### 添加新处理器

1. 在 `app/core/` 创建处理器类
2. 实现统一接口 (process 方法)
3. 添加单元测试
4. 在 API 中调用

**示例**:
```python
# app/core/custom_processor.py
from pathlib import Path
from typing import Tuple, List

class CustomProcessor:
    def process(self, file_path: str, doc_id: str, output_dir: str) -> Tuple[str, List[str]]:
        # 处理逻辑
        markdown_content = "..."
        image_paths = [...]
        return markdown_content, image_paths
```

## 错误处理

### HTTP 异常

```python
from fastapi import HTTPException

# 文件不存在
raise HTTPException(status_code=404, detail="文档不存在")

# 文件格式不支持
raise HTTPException(status_code=400, detail="不支持的文件格式")

# 文件过大
raise HTTPException(status_code=400, detail="文件大小超出限制")
```

### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

logger.info("文档上传成功: doc_id=%s", doc_id)
logger.error("文档处理失败: doc_id=%s, error=%s", doc_id, str(e))
```

## 性能优化

### 异步处理

- 使用 `async/await` 处理 I/O 操作
- 后台任务处理耗时操作 (Phase 2)
- 流式响应减少延迟 (Phase 3)

### 缓存策略 (计划)

- 已处理的文档缓存
- Token 计数结果缓存
- API 响应缓存

## 常见问题

### Q: Pix2Text 安装失败

A: 先安装 PyTorch
```bash
pip install torch torchvision
pip install pix2text
```

### Q: Qwen API 调用超时

A: 检查网络和 API 密钥，增加超时时间
```python
responses = Generation.call(
    ...,
    timeout=30  # 增加超时
)
```

### Q: 文件上传失败

A: 检查文件大小限制和目录权限
```python
# 检查配置
settings.max_file_size  # 默认 10MB
settings.upload_dir     # 确保有写权限
```

## 相关文件

- **主入口**: `app/main.py`
- **配置**: `app/config.py`
- **API 路由**: `app/api/v1/`
- **核心逻辑**: `app/core/`
- **数据模型**: `app/models/`
- **依赖列表**: `requirements.txt`
- **环境变量**: `.env.example`
- **文档**: `README.md`
