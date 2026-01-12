# PaperReader2 Backend

AI融合论文辅助阅读器 - 后端服务

## 📋 项目概述

PaperReader2 是一个基于 FastAPI 的本地部署论文阅读器后端服务,提供文档上传、PDF转Markdown、AI问答等功能。

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Windows 11 / Linux / macOS

### 安装步骤

#### 1. 创建虚拟环境

```bash
cd backend
python -m venv venv
```

#### 2. 激活虚拟环境

**Windows PowerShell:**
```bash
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**
```bash
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

编辑 `.env` 文件,配置必要的环境变量:

```env
# API配置
API_HOST=127.0.0.1
API_PORT=8000

# Qwen API密钥(从系统环境变量读取)
DASHSCOPE_API_KEY=your_api_key_here
```

#### 5. 启动服务

```bash
python -m app.main
```

或使用 uvicorn:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

服务启动后访问:
- API文档: http://127.0.0.1:8000/api/docs
- 健康检查: http://127.0.0.1:8000/api/v1/health

## 📁 项目结构

```
backend/
├── app/                          # 应用代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI应用入口
│   ├── config.py                 # 配置管理
│   │
│   ├── api/                      # API路由层
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── documents.py      # 文档管理API
│   │       ├── chat.py           # AI聊天API
│   │       └── health.py         # 健康检查API
│   │
│   ├── core/                     # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── pdf_processor.py      # PDF处理器(含GPU加速)
│   │   ├── docx_processor.py     # DOCX处理器(Phase 3 - 未实现)
│   │   ├── context_builder.py    # 上下文构建器(Phase 3 - 未实现)
│   │   └── llm_service.py        # LLM调用服务(Phase 3 - 未实现)
│   │
│   ├── models/                   # Pydantic数据模型
│   │   └── __init__.py
│   │
│   ├── utils/                    # 工具函数
│   │   └── __init__.py
│   │
│   └── storage/                  # 存储管理
│       └── __init__.py
│
├── data/                         # 数据目录(运行时创建)
│   ├── uploads/                  # 原始上传文件
│   └── processed/                # 处理后的文件
│
├── tests/                        # 测试代码
│   └── __init__.py
│
├── requirements.txt              # Python依赖
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量示例
└── README.md                     # 本文档
```

## 🔌 API端点

### 健康检查

- `GET /api/v1/health` - 获取系统健康状态
- `GET /api/v1/health/ping` - 快速ping检查

### 文档管理

- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/list` - 获取文档列表
- `GET /api/v1/documents/{doc_id}` - 获取文档内容
- `DELETE /api/v1/documents/{doc_id}` - 删除文档

### AI聊天 (Phase 3 - 未实现)

> 🚧 此端点尚未实现

- `POST /api/v1/chat/message` - 发送聊天消息

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| API_HOST | API服务主机 | 127.0.0.1 |
| API_PORT | API服务端口 | 8000 |
| API_PREFIX | API前缀 | /api/v1 |
| DASHSCOPE_API_KEY | Qwen API密钥 | - |
| QWEN_MODEL | Qwen模型名称 | qwen-plus |
| UPLOAD_DIR | 上传文件目录 | ./data/uploads |
| PROCESSED_DIR | 处理后文件目录 | ./data/processed |
| CORS_ORIGINS | 允许的CORS源 | ["http://localhost:5173"] |
| LOG_LEVEL | 日志级别 | INFO |
| MAX_FILE_SIZE | 最大文件大小(字节) | 10485760 (10MB) |
| PAPERREADER_DEVICE | GPU设备控制 | auto (cuda/cpu) |
| USE_MARKER | 是否使用marker-pdf | false |

### DASHSCOPE_API_KEY 配置

推荐从系统环境变量读取API密钥:

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="your_api_key_here"
```

**Windows CMD:**
```cmd
set DASHSCOPE_API_KEY=your_api_key_here
```

**Linux/macOS:**
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

## 🧪 测试

### 运行测试

```bash
pytest
```

### 运行特定测试

```bash
pytest tests/test_pdf_processor.py
```

### 测试覆盖率

```bash
pytest --cov=app --cov-report=html
```

## 📝 开发计划

### ✅ Phase 1: 环境搭建与基础框架(已完成)
- [x] 创建项目目录结构
- [x] 配置Python虚拟环境
- [x] 创建FastAPI应用入口
- [x] 实现配置管理
- [x] 实现健康检查API
- [x] 实现文件上传API
- [x] 配置CORS

### ✅ Phase 2: PDF处理与Markdown渲染(已完成)
- [x] 实现PDFProcessor类
- [x] 集成Pix2Text进行OCR
- [x] 集成PyMuPDF提取图像
- [x] 实现Markdown生成逻辑
- [x] GPU自动检测和加速
- [x] 错误处理机制

### 📋 Phase 3: AI问答功能(计划中)
- [ ] 实现ContextBuilder类
- [ ] 实现LLMService类
- [ ] 实现流式响应
- [ ] 实现聊天API端点
- [ ] 实现DOCXProcessor

## 🛠️ 技术栈

- **Web框架**: FastAPI 0.109.0
- **PDF处理**: Pix2Text 1.1.0+ + PyMuPDF 1.23.8
- **LLM调用**: DashScope 1.14.0+ (Qwen, Phase 3)
- **数据验证**: Pydantic 2.9.2+
- **ASGI服务器**: Uvicorn 0.27.0

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📮 联系方式

如有问题,请通过 GitHub Issues 联系。
