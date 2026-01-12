# PaperReader2 - AI融合论文辅助阅读器开发计划

## 📋 项目背景

**项目名称**：PaperReader2
**项目类型**：本地部署的AI增强型论文阅读器
**开发目标**：快速构建MVP（最小可行产品），后续迭代优化
**技术特点**：简化架构、快速处理、成本可控

---

## 🎯 核心需求

### 功能需求
1. **文档上传与转换**
   - 支持PDF、DOCX格式上传
   - 自动转换为Markdown格式
   - 保留文档中的图像（高分辨率）
   - 支持数学公式（LaTeX格式）

2. **AI问答功能**
   - 基于上传的论文内容进行智能问答
   - 使用Qwen大模型
   - 流式响应，实时显示回答
   - 支持对话历史

3. **文档浏览**
   - Markdown渲染（支持公式、图像、表格）
   - 文档目录导航
   - 文档列表管理

### 非功能需求
- 本地部署，数据隐私安全
- 处理速度快（优先使用Pix2Text）
- 界面友好，操作简单
- Windows 11兼容

---

## 🏗️ 技术架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (React + Vite)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  文件上传    │  │  文档查看    │  │  AI聊天      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓ HTTP/SSE
┌─────────────────────────────────────────────────────────┐
│               API网关层 (FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  文档API     │  │  聊天API     │  │  静态资源    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              业务逻辑层 (Core Services)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  文档处理    │  │  上下文管理  │  │  LLM服务     │  │
│  │  Pix2Text    │  │  Token计数   │  │  Qwen API    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│             数据存储层 (本地文件系统)                   │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  uploads/    │  │  processed/  │                    │
│  │  原始文件    │  │  MD + 图像   │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### 技术栈选型

#### 后端技术栈
| 模块 | 技术选型 | 版本要求 | 选型理由 |
|------|---------|---------|---------|
| **Web框架** | FastAPI | >=0.109.0 | 高性能、自动文档、原生异步 |
| **PDF处理** | Pix2Text | >=1.1.0 | 速度快、支持OCR和公式识别 |
| **PDF辅助** | PyMuPDF | 1.23.8 | 高质量图像提取 |
| **DOCX处理** | python-docx | 1.1.0 | 官方推荐库 |
| **LLM调用** | dashscope | >=1.14.0 | 阿里云Qwen官方SDK |
| **Token计数** | tiktoken | >=0.5.0 | 准确的Token统计 |
| **数据验证** | Pydantic | 2.5.3 | FastAPI原生集成 |

#### 前端技术栈
| 模块 | 技术选型 | 版本要求 | 选型理由 |
|------|---------|---------|---------|
| **框架** | React | ^18.2.0 | 成熟、生态丰富 |
| **构建工具** | Vite | ^5.0.12 | 快速、现代化 |
| **语言** | TypeScript | ^5.3.3 | 类型安全 |
| **状态管理** | Zustand | ^4.5.0 | 轻量、简单 |
| **Markdown渲染** | react-markdown | ^9.0.1 | 功能完整 |
| **公式渲染** | KaTeX | ^0.16.9 | 快速、轻量 |
| **样式** | Tailwind CSS | ^3.4.1 | 开发效率高 |
| **HTTP客户端** | axios | ^1.6.5 | API友好 |

---

## 📁 项目目录结构

```
paperreader2/
├── backend/                          # 后端项目根目录
│   ├── app/                          # 应用代码
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI应用入口
│   │   ├── config.py                 # 配置管理（读取环境变量）
│   │   │
│   │   ├── api/                      # API路由层
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── documents.py      # 文档管理API
│   │   │       ├── chat.py           # AI聊天API
│   │   │       └── health.py         # 健康检查API
│   │   │
│   │   ├── core/                     # 核心业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py # 文档处理基类
│   │   │   ├── pdf_processor.py      # PDF处理器（Pix2Text）
│   │   │   ├── docx_processor.py     # DOCX处理器
│   │   │   ├── image_handler.py      # 图像提取与管理
│   │   │   ├── context_builder.py    # 上下文构建器
│   │   │   └── llm_service.py        # Qwen LLM调用服务
│   │   │
│   │   ├── models/                   # Pydantic数据模型
│   │   │   ├── __init__.py
│   │   │   ├── document.py           # 文档模型
│   │   │   ├── chat.py               # 聊天模型
│   │   │   └── response.py           # API响应模型
│   │   │
│   │   ├── utils/                    # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── file_utils.py         # 文件操作工具
│   │   │   ├── markdown_utils.py     # Markdown处理工具
│   │   │   └── logger.py             # 日志工具
│   │   │
│   │   └── storage/                  # 存储管理
│   │       ├── __init__.py
│   │       └── file_storage.py       # 本地文件存储管理
│   │
│   ├── data/                         # 数据目录（运行时创建）
│   │   ├── uploads/                  # 原始上传文件
│   │   │   └── {doc_id}/
│   │   │       └── original.pdf
│   │   └── processed/                # 处理后的文件
│   │       ├── markdown/             # Markdown文件
│   │       │   └── {doc_id}.md
│   │       └── images/               # 提取的图像
│   │           └── {doc_id}/
│   │               ├── img_001.png
│   │               └── img_002.png
│   │
│   ├── tests/                        # 测试代码
│   │   ├── __init__.py
│   │   ├── test_pdf_processor.py
│   │   └── test_llm_service.py
│   │
│   ├── requirements.txt              # Python依赖
│   ├── .env.example                  # 环境变量示例
│   └── README.md                     # 后端说明文档
│
├── frontend/                         # 前端项目根目录
│   ├── src/
│   │   ├── components/               # React组件
│   │   │   ├── upload/               # 上传相关组件
│   │   │   │   ├── FileUploader.tsx  # 文件上传器
│   │   │   │   └── UploadProgress.tsx # 上传进度
│   │   │   │
│   │   │   ├── document/             # 文档相关组件
│   │   │   │   ├── DocumentViewer.tsx    # 文档查看器
│   │   │   │   ├── MarkdownRenderer.tsx  # Markdown渲染器
│   │   │   │   ├── DocumentList.tsx      # 文档列表
│   │   │   │   └── TableOfContents.tsx   # 目录导航
│   │   │   │
│   │   │   ├── chat/                 # 聊天相关组件
│   │   │   │   ├── ChatInterface.tsx     # 聊天界面
│   │   │   │   ├── MessageList.tsx       # 消息列表
│   │   │   │   ├── MessageInput.tsx      # 消息输入框
│   │   │   │   └── StreamingMessage.tsx  # 流式消息显示
│   │   │   │
│   │   │   └── common/               # 通用组件
│   │   │       ├── Loading.tsx
│   │   │       ├── ErrorBoundary.tsx
│   │   │       └── Button.tsx
│   │   │
│   │   ├── hooks/                    # 自定义React Hooks
│   │   │   ├── useDocument.ts        # 文档管理Hook
│   │   │   ├── useChat.ts            # 聊天Hook
│   │   │   └── useStreamingResponse.ts # 流式响应Hook
│   │   │
│   │   ├── services/                 # API服务层
│   │   │   ├── api.ts                # Axios配置
│   │   │   ├── documentService.ts    # 文档API调用
│   │   │   └── chatService.ts        # 聊天API调用
│   │   │
│   │   ├── store/                    # Zustand状态管理
│   │   │   ├── documentStore.ts      # 文档状态
│   │   │   └── chatStore.ts          # 聊天状态
│   │   │
│   │   ├── types/                    # TypeScript类型定义
│   │   │   ├── document.ts
│   │   │   ├── chat.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── utils/                    # 工具函数
│   │   │   ├── formatters.ts
│   │   │   └── validators.ts
│   │   │
│   │   ├── styles/                   # 样式文件
│   │   │   ├── globals.css
│   │   │   └── markdown.css
│   │   │
│   │   ├── App.tsx                   # 根组件
│   │   ├── main.tsx                  # 入口文件
│   │   └── vite-env.d.ts
│   │
│   ├── public/                       # 静态资源
│   │   └── favicon.ico
│   │
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── scripts/                          # 工具脚本
│   ├── setup.bat                     # 环境初始化脚本
│   ├── start_backend.bat             # 启动后端
│   ├── start_frontend.bat            # 启动前端
│   └── start_all.bat                 # 同时启动前后端
│
├── docs/                             # 文档目录
│   ├── architecture.md               # 架构设计文档
│   ├── api.md                        # API接口文档
│   └── deployment.md                 # 部署指南
│
├── .gitignore
├── README.md                         # 项目说明
└── devplan.md                        # 本开发计划文档
```

---

## 🔄 核心数据流设计

### 1. 文档上传与处理流程

```
用户操作：选择PDF/DOCX文件 → 点击上传
                ↓
前端处理：
    1. 文件验证（格式、大小）
    2. 创建上传请求
    3. 显示上传进度条
    4. 调用 POST /api/v1/documents/upload
                ↓
后端接收：
    1. 接收文件流
    2. 生成唯一文档ID (UUID)
    3. 保存原始文件到 data/uploads/{doc_id}/
    4. 返回文档ID和处理状态
    5. 触发后台异步任务
                ↓
后台任务（AsyncIO）：
    1. 根据文件扩展名选择处理器
       - .pdf → PDFProcessor
       - .docx → DOCXProcessor

    2. PDF处理流程（Pix2Text）：
       ├─ 使用Pix2Text进行OCR识别
       ├─ 提取文本内容（保持结构）
       ├─ 识别数学公式（转为LaTeX）
       ├─ 使用PyMuPDF提取高质量图像
       ├─ 保存图像到 data/processed/images/{doc_id}/
       └─ 生成Markdown文件

    3. DOCX处理流程（python-docx）：
       ├─ 提取段落和样式
       ├─ 提取嵌入图像
       ├─ 转换MathML公式为LaTeX
       └─ 生成Markdown文件

    4. 保存Markdown到 data/processed/markdown/{doc_id}.md

    5. 更新文档状态为 "ready"
                ↓
前端轮询/SSE通知：
    1. 前端定期调用 GET /api/v1/documents/{doc_id}/status
    2. 状态变为 "ready" 后停止轮询
    3. 自动跳转到文档查看页面
                ↓
文档渲染：
    1. 调用 GET /api/v1/documents/{doc_id}
    2. 获取Markdown内容
    3. 使用react-markdown渲染
    4. KaTeX渲染数学公式
    5. 懒加载显示图像
```

### 2. AI问答流程

```
用户操作：在聊天框输入问题 → 点击发送
                ↓
前端处理：
    1. 验证输入非空
    2. 添加消息到聊天历史
    3. 调用 POST /api/v1/chat/message
    4. 建立SSE连接接收流式响应
                ↓
后端处理（chat.py）：
    1. 接收请求参数
       - doc_id: 文档ID
       - question: 用户问题
       - history: 对话历史

    2. 调用 ContextBuilder.build()
       ├─ 读取 data/processed/markdown/{doc_id}.md
       ├─ 统计总Token数（使用tiktoken）
       ├─ 如果超过限制（如128k），执行智能截断：
       │  ├─ 优先保留：标题、摘要、引言、结论
       │  ├─ 其次保留：方法、实验结果
       │  └─ 最后保留：参考文献等
       └─ 构建系统提示词

    3. 调用 LLMService.stream_chat()
       ├─ 构建完整Prompt：
       │  ```
       │  System: 你是一个专业的学术论文阅读助手...
       │
       │  以下是论文内容：
       │  {markdown_content}
       │
       │  对话历史：
       │  {chat_history}
       │
       │  用户问题：{question}
       │  ```
       ├─ 调用Qwen API（流式模式）
       │  - API: https://dashscope.aliyuncs.com/compatible-mode/v1
       │  - Model: qwen-turbo / qwen-plus
       │  - Stream: true
       └─ 逐块返回响应
                ↓
流式响应（SSE）：
    1. 后端使用 StreamingResponse
    2. 每个Token生成后立即发送
    3. 格式：data: {\"content\": \"token\", \"done\": false}
    4. 结束标记：data: {\"done\": true}
                ↓
前端显示：
    1. 监听SSE事件
    2. 逐字显示回答（打字机效果）
    3. 完成后保存到对话历史
    4. 允许继续提问
```

### 3. 文档列表管理流程

```
用户操作：打开应用首页
                ↓
前端调用：GET /api/v1/documents/list
                ↓
后端处理：
    1. 扫描 data/uploads/ 目录
    2. 读取每个文档的元数据
    3. 返回文档列表：
       - doc_id
       - filename
       - upload_time
       - status (processing/ready/error)
       - file_size
                ↓
前端显示：
    1. 渲染文档列表卡片
    2. 显示处理状态
    3. 提供操作按钮：
       - 查看文档
       - 开始聊天
       - 删除文档
```

---

## 🔧 关键模块详细设计

### 1. PDF处理模块（backend/app/core/pdf_processor.py）

#### 核心职责
- 使用Pix2Text进行OCR识别和公式提取
- 使用PyMuPDF提取高质量图像
- 生成结构化的Markdown文档

#### 实现方案

```python
from pix2text import Pix2Text
import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple, List

class PDFProcessor:
    """PDF文档处理器，使用Pix2Text和PyMuPDF"""

    def __init__(self):
        # 初始化Pix2Text（支持公式识别）
        self.p2t = Pix2Text.from_config()

    def process(self, pdf_path: str, doc_id: str, output_dir: str) -> Tuple[str, List[str]]:
        """
        处理PDF文件，返回Markdown内容和图像路径列表

        Args:
            pdf_path: PDF文件路径
            doc_id: 文档ID
            output_dir: 输出目录

        Returns:
            (markdown_content, image_paths)
        """
        # 1. 使用Pix2Text进行全文识别
        markdown_content = self._ocr_with_pix2text(pdf_path)

        # 2. 使用PyMuPDF提取高质量图像
        image_paths = self._extract_images_with_pymupdf(
            pdf_path, doc_id, output_dir
        )

        # 3. 在Markdown中插入图像引用
        final_markdown = self._insert_image_references(
            markdown_content, image_paths
        )

        return final_markdown, image_paths

    def _ocr_with_pix2text(self, pdf_path: str) -> str:
        """使用Pix2Text进行OCR识别"""
        # Pix2Text支持直接处理PDF
        result = self.p2t.recognize_pdf(
            pdf_path,
            return_text=True,
            rec_config={'formula_ocr': True}  # 启用公式识别
        )

        # 结果已经是Markdown格式（包含LaTeX公式）
        return result['text']

    def _extract_images_with_pymupdf(
        self, pdf_path: str, doc_id: str, output_dir: str
    ) -> List[str]:
        """使用PyMuPDF提取高质量图像"""
        doc = fitz.open(pdf_path)
        image_dir = Path(output_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        img_index = 1

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img in image_list:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # 保存图像
                img_filename = f"img_{img_index:03d}.png"
                img_path = image_dir / img_filename

                with open(img_path, "wb") as f:
                    f.write(image_bytes)

                image_paths.append(str(img_path))
                img_index += 1

        doc.close()
        return image_paths

    def _insert_image_references(
        self, markdown: str, image_paths: List[str]
    ) -> str:
        """在Markdown中插入图像引用"""
        # 简化版：在文档末尾添加所有图像
        # 实际实现可以更智能地插入图像位置

        if not image_paths:
            return markdown

        images_section = "\n\n## 文档图像\n\n"
        for i, img_path in enumerate(image_paths, 1):
            # 转换为相对API路径
            img_id = Path(img_path).stem
            doc_id = Path(img_path).parent.name
            api_path = f"/api/v1/documents/{doc_id}/images/{img_id}"
            images_section += f"![图{i}]({api_path})\n\n"

        return markdown + images_section

# 配置选项：支持升级到marker-pdf
USE_MARKER = False  # 从环境变量读取

if USE_MARKER:
    # 未来升级选项
    # from marker.convert import convert_single_pdf
    pass
```

#### 关键技术点

1. **Pix2Text优势**
   - 开箱即用的公式识别能力
   - 支持中英文混排
   - 直接输出Markdown格式
   - 处理速度快

2. **PyMuPDF优势**
   - 提取原始高质量图像（非截图）
   - 速度快、内存占用小
   - 支持各种PDF格式

3. **升级路径**
   - 通过环境变量 `USE_MARKER=true` 可切换到marker-pdf
   - marker-pdf提供更高质量的布局识别
   - 适合对质量要求极高的场景

---

### 2. 上下文构建模块（backend/app/core/context_builder.py）

#### 核心职责
- 读取Markdown文档内容
- 统计Token数量
- 智能截断长文档
- 管理对话历史

#### 实现方案

```python
import tiktoken
from typing import List, Dict
from pathlib import Path

class ContextBuilder:
    """上下文构建器，管理文档内容和对话历史"""

    def __init__(self, max_tokens: int = 120000):
        """
        初始化上下文构建器

        Args:
            max_tokens: 最大Token数（留出余量给回复）
        """
        self.max_tokens = max_tokens
        # 使用tiktoken统计Token（兼容多种模型）
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def build_context(
        self,
        doc_id: str,
        question: str,
        chat_history: List[Dict[str, str]],
        markdown_dir: str
    ) -> str:
        """
        构建完整的上下文Prompt

        Args:
            doc_id: 文档ID
            question: 用户问题
            chat_history: 对话历史 [{"role": "user", "content": "..."}, ...]
            markdown_dir: Markdown文件目录

        Returns:
            完整的Prompt字符串
        """
        # 1. 读取文档内容
        md_path = Path(markdown_dir) / f"{doc_id}.md"
        with open(md_path, "r", encoding="utf-8") as f:
            document_content = f.read()

        # 2. 统计各部分Token
        doc_tokens = self._count_tokens(document_content)
        history_tokens = self._count_tokens(
            self._format_history(chat_history)
        )
        question_tokens = self._count_tokens(question)
        system_tokens = 500  # 系统提示词预估

        total_tokens = (
            doc_tokens + history_tokens +
            question_tokens + system_tokens
        )

        # 3. 如果超过限制，智能截断文档
        if total_tokens > self.max_tokens:
            target_doc_tokens = (
                self.max_tokens - history_tokens -
                question_tokens - system_tokens
            )
            document_content = self._truncate_document(
                document_content, target_doc_tokens
            )

        # 4. 构建完整Prompt
        prompt = self._build_prompt(
            document_content, chat_history, question
        )

        return prompt

    def _count_tokens(self, text: str) -> int:
        """统计文本的Token数量"""
        return len(self.encoder.encode(text))

    def _truncate_document(
        self, content: str, target_tokens: int
    ) -> str:
        """
        智能截断文档内容

        策略：
        1. 优先保留：标题、摘要、引言、结论
        2. 其次保留：方法、实验结果
        3. 最后保留：详细描述、参考文献
        """
        sections = self._parse_sections(content)

        # 定义优先级
        priority_keywords = {
            'high': ['abstract', 'introduction', 'conclusion',
                     '摘要', '引言', '结论'],
            'medium': ['method', 'experiment', 'result',
                       '方法', '实验', '结果'],
            'low': ['reference', 'appendix', '参考文献', '附录']
        }

        # 按优先级选择章节
        selected_content = []
        current_tokens = 0

        # 先添加高优先级章节
        for section in sections:
            if any(kw in section['title'].lower()
                   for kw in priority_keywords['high']):
                section_tokens = self._count_tokens(section['content'])
                if current_tokens + section_tokens <= target_tokens:
                    selected_content.append(section['content'])
                    current_tokens += section_tokens

        # 如果还有空间，添加中优先级章节
        if current_tokens < target_tokens:
            for section in sections:
                if any(kw in section['title'].lower()
                       for kw in priority_keywords['medium']):
                    section_tokens = self._count_tokens(
                        section['content']
                    )
                    if current_tokens + section_tokens <= target_tokens:
                        selected_content.append(section['content'])
                        current_tokens += section_tokens

        return "\n\n".join(selected_content)

    def _parse_sections(self, content: str) -> List[Dict[str, str]]:
        """解析Markdown章节"""
        sections = []
        current_section = None

        for line in content.split('\n'):
            if line.startswith('# ') or line.startswith('## '):
                if current_section:
                    sections.append(current_section)
                current_section = {
                    'title': line.strip('# '),
                    'content': line + '\n'
                }
            elif current_section:
                current_section['content'] += line + '\n'

        if current_section:
            sections.append(current_section)

        return sections

    def _format_history(self, chat_history: List[Dict]) -> str:
        """格式化对话历史"""
        formatted = []
        for msg in chat_history[-10:]:  # 只保留最近10轮对话
            role = "用户" if msg["role"] == "user" else "助手"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _build_prompt(
        self, document: str, history: List[Dict], question: str
    ) -> str:
        """构建最终Prompt"""
        system_prompt = """你是一个专业的学术论文阅读助手。你的任务是帮助用户理解和分析论文内容。

请遵循以下原则：
1. 仅基于提供的论文内容回答问题
2. 如果论文中没有相关信息，请明确告知用户
3. 回答要准确、简洁、有条理
4. 可以引用论文中的具体内容
5. 对于复杂概念，提供清晰的解释"""

        prompt = f"""{system_prompt}

## 论文内容

{document}

## 对话历史

{self._format_history(history)}

## 用户问题

{question}

请根据以上论文内容回答用户问题："""

        return prompt
```

#### 关键技术点

1. **Token计数**
   - 使用tiktoken库精确计数
   - 兼容多种模型的Token计算方式

2. **智能截断**
   - 基于章节语义的截断
   - 优先保留关键信息
   - 避免破坏上下文连贯性

3. **对话历史管理**
   - 只保留最近N轮对话
   - 避免历史过长占用上下文

---

### 3. LLM服务模块（backend/app/core/llm_service.py）

#### 核心职责
- 调用Qwen API
- 支持流式响应
- 错误处理和重试

#### 实现方案

```python
import os
from typing import AsyncGenerator, Optional
from dashscope import Generation
import dashscope

class LLMService:
    """Qwen大模型调用服务"""

    def __init__(self):
        # 从环境变量读取API密钥
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable not set")

        dashscope.api_key = self.api_key

        # 模型配置
        self.model = "qwen-plus"  # 可选: qwen-turbo, qwen-max
        self.temperature = 0.3    # 低温度确保准确性

    async def stream_chat(
        self,
        prompt: str,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """
        流式调用Qwen API

        Args:
            prompt: 完整的Prompt
            max_tokens: 最大生成Token数

        Yields:
            生成的文本片段
        """
        try:
            responses = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=self.temperature,
                result_format='message',  # 使用message格式
                stream=True,              # 启用流式输出
                incremental_output=True   # 增量输出
            )

            for response in responses:
                if response.status_code == 200:
                    # 提取生成的文本
                    chunk = response.output.choices[0].message.content
                    yield chunk
                else:
                    # 错误处理
                    error_msg = (
                        f"API调用失败: {response.code} - "
                        f"{response.message}"
                    )
                    yield f"\n\n[错误: {error_msg}]"
                    break

        except Exception as e:
            error_msg = f"LLM服务异常: {str(e)}"
            yield f"\n\n[错误: {error_msg}]"

    async def chat(
        self,
        prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """
        非流式调用（用于测试）

        Args:
            prompt: 完整的Prompt
            max_tokens: 最大生成Token数

        Returns:
            完整的回答文本
        """
        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=self.temperature,
                result_format='message'
            )

            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                return f"API调用失败: {response.code} - {response.message}"

        except Exception as e:
            return f"LLM服务异常: {str(e)}"
```

#### API配置

根据环境变量配置：
- `DASHSCOPE_API_KEY`: sk-82d82b70e6dc42829b9d5c843e0ebab8
- `QWEN_API_BASE`: https://dashscope.aliyuncs.com/compatible-mode/v1

#### 模型选择

| 模型 | 上下文长度 | 速度 | 成本 | 推荐场景 |
|------|-----------|------|------|---------|
| qwen-turbo | 8k | 快 | 低 | 简单问答、快速响应 |
| qwen-plus | 128k | 中 | 中 | **推荐：论文阅读** |
| qwen-max | 8k | 慢 | 高 | 复杂推理、高质量回答 |

**MVP阶段推荐**：qwen-plus（上下文长度足够，性价比高）

---

### 4. FastAPI路由设计

#### 文档API（backend/app/api/v1/documents.py）

```python
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import uuid
from typing import List

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    上传文档并启动异步处理

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

    # 2. 生成唯一文档ID
    doc_id = str(uuid.uuid4())

    # 3. 保存原始文件
    upload_dir = Path("data/uploads") / doc_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"original{file_ext}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 4. 添加后台处理任务
    background_tasks.add_task(
        process_document,
        doc_id=doc_id,
        file_path=str(file_path),
        file_type=file_ext[1:]  # 去掉点号
    )

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "status": "processing",
        "message": "文档正在处理中，请稍候..."
    }

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """获取处理后的文档内容"""
    md_path = Path("data/processed/markdown") / f"{doc_id}.md"

    if not md_path.exists():
        raise HTTPException(
            status_code=404,
            detail="文档不存在或正在处理中"
        )

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "doc_id": doc_id,
        "content": content,
        "status": "ready"
    }

@router.get("/{doc_id}/images/{image_name}")
async def get_image(doc_id: str, image_name: str):
    """获取文档中的图像"""
    img_path = Path("data/processed/images") / doc_id / f"{image_name}.png"

    if not img_path.exists():
        raise HTTPException(status_code=404, detail="图像不存在")

    return FileResponse(img_path, media_type="image/png")

@router.get("/list")
async def list_documents():
    """获取所有文档列表"""
    uploads_dir = Path("data/uploads")

    if not uploads_dir.exists():
        return {"documents": []}

    documents = []
    for doc_dir in uploads_dir.iterdir():
        if doc_dir.is_dir():
            doc_id = doc_dir.name

            # 检查处理状态
            md_path = Path("data/processed/markdown") / f"{doc_id}.md"
            status = "ready" if md_path.exists() else "processing"

            # 获取原始文件信息
            original_files = list(doc_dir.glob("original.*"))
            if original_files:
                original_file = original_files[0]
                documents.append({
                    "doc_id": doc_id,
                    "filename": original_file.name,
                    "status": status,
                    "upload_time": original_file.stat().st_ctime
                })

    # 按上传时间倒序排序
    documents.sort(key=lambda x: x["upload_time"], reverse=True)

    return {"documents": documents}

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档及其所有相关文件"""
    import shutil

    # 删除上传文件
    upload_dir = Path("data/uploads") / doc_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    # 删除Markdown文件
    md_path = Path("data/processed/markdown") / f"{doc_id}.md"
    if md_path.exists():
        md_path.unlink()

    # 删除图像目录
    image_dir = Path("data/processed/images") / doc_id
    if image_dir.exists():
        shutil.rmtree(image_dir)

    return {"message": "文档已删除", "doc_id": doc_id}


# 后台处理函数
async def process_document(doc_id: str, file_path: str, file_type: str):
    """后台异步处理文档"""
    try:
        if file_type == "pdf":
            from app.core.pdf_processor import PDFProcessor
            processor = PDFProcessor()
        elif file_type == "docx":
            from app.core.docx_processor import DOCXProcessor
            processor = DOCXProcessor()
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

        # 处理文档
        markdown_content, image_paths = processor.process(
            file_path, doc_id, "data/processed"
        )

        # 保存Markdown
        md_dir = Path("data/processed/markdown")
        md_dir.mkdir(parents=True, exist_ok=True)

        md_path = md_dir / f"{doc_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    except Exception as e:
        # 记录错误日志
        print(f"文档处理失败: {doc_id}, 错误: {str(e)}")
        # TODO: 更新文档状态为error
```

#### 聊天API（backend/app/api/v1/chat.py）

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
import json

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    doc_id: str
    question: str
    history: List[Dict[str, str]] = []

@router.post("/message")
async def chat_message(request: ChatRequest):
    """
    发送聊天消息，返回流式响应

    请求体:
    {
        "doc_id": "文档ID",
        "question": "用户问题",
        "history": [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"}
        ]
    }
    """
    from app.core.context_builder import ContextBuilder
    from app.core.llm_service import LLMService

    # 1. 构建上下文
    context_builder = ContextBuilder()
    try:
        prompt = context_builder.build_context(
            doc_id=request.doc_id,
            question=request.question,
            chat_history=request.history,
            markdown_dir="data/processed/markdown"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="文档不存在，请先上传并处理文档"
        )

    # 2. 调用LLM服务（流式）
    llm_service = LLMService()

    async def generate():
        """生成器函数，用于SSE流式传输"""
        try:
            async for chunk in llm_service.stream_chat(prompt):
                # SSE格式：data: {json}\n\n
                data = {
                    "content": chunk,
                    "done": False
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 发送结束标记
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            error_data = {
                "error": str(e),
                "done": True
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/history/{doc_id}")
async def get_chat_history(doc_id: str):
    """
    获取文档的聊天历史

    注意：MVP阶段暂不持久化历史，由前端管理
    """
    # TODO: 实现历史记录持久化
    return {"history": []}
```

---

## 📦 依赖配置

### backend/requirements.txt

```txt
# Web框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# PDF处理
pix2text>=1.1.0           # 主要方案：OCR + 公式识别
pymupdf==1.23.8           # 图像提取
# marker-pdf>=0.2.6       # 升级选项（注释，按需启用）

# DOCX处理
python-docx==1.1.0

# LLM
dashscope>=1.14.0         # 阿里云Qwen SDK

# Token计数
tiktoken>=0.5.0

# 数据处理
pydantic==2.5.3
pydantic-settings==2.1.0

# 工具
aiofiles==23.2.1
python-dotenv==1.0.0

# 开发工具
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### frontend/package.json

```json
{
  "name": "paperreader2-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "remark-math": "^6.0.0",
    "rehype-katex": "^7.0.0",
    "katex": "^0.16.9",
    "axios": "^1.6.5",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.12",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17"
  }
}
```

---

## 🚀 开发计划与里程碑

### Phase 1: 环境搭建与基础框架（第1-2周）

#### 目标
- 搭建前后端开发环境
- 实现基础的文件上传功能
- 验证技术栈可行性

#### 后端任务
- [ ] 创建项目目录结构
- [ ] 配置Python虚拟环境
- [ ] 安装依赖（requirements.txt）
- [ ] 创建FastAPI应用入口（main.py）
- [ ] 实现配置管理（config.py）
- [ ] 实现文件上传API
- [ ] 实现健康检查API
- [ ] 配置CORS

#### 前端任务
- [ ] 创建React项目（Vite）
- [ ] 配置TypeScript
- [ ] 配置Tailwind CSS
- [ ] 创建基础布局组件
- [ ] 实现文件上传组件
- [ ] 配置Axios

#### 验收标准
- ✅ 前后端可以正常启动
- ✅ 可以通过前端上传文件到后端
- ✅ 后端可以保存文件到指定目录

---

### Phase 2: PDF处理与Markdown渲染（第3-4周）

#### 目标
- 实现PDF转Markdown核心功能
- 支持图像和公式渲染

#### 后端任务
- [ ] 实现PDFProcessor类
- [ ] 集成Pix2Text进行OCR
- [ ] 集成PyMuPDF提取图像
- [ ] 实现Markdown生成逻辑
- [ ] 实现图像API端点
- [ ] 实现文档状态查询API
- [ ] 添加后台异步任务

#### 前端任务
- [ ] 实现Markdown渲染组件
- [ ] 集成KaTeX渲染公式
- [ ] 实现图像懒加载
- [ ] 实现文档查看页面
- [ ] 添加文档列表页面
- [ ] 实现状态轮询

#### 验收标准
- ✅ PDF可以正确转换为Markdown
- ✅ 数学公式正确显示（LaTeX格式）
- ✅ 图像正确提取和显示
- ✅ 文档可以正常浏览

---

### Phase 3: AI问答功能（第5-6周）

#### 目标
- 实现基于上下文的AI问答
- 支持流式响应

#### 后端任务
- [ ] 实现ContextBuilder类
- [ ] 集成tiktoken进行Token计数
- [ ] 实现智能截断逻辑
- [ ] 实现LLMService类
- [ ] 集成Qwen API
- [ ] 实现流式响应
- [ ] 实现聊天API端点

#### 前端任务
- [ ] 实现聊天界面组件
- [ ] 实现消息列表组件
- [ ] 实现消息输入组件
- [ ] 实现SSE流式接收
- [ ] 实现打字机效果
- [ ] 实现对话历史管理

#### 验收标准
- ✅ 可以基于文档内容进行问答
- ✅ 流式响应体验流畅
- ✅ 对话历史正确管理
- ✅ 错误处理完善

---

### Phase 4: 优化与完善（第7-8周）

#### 目标
- 性能优化
- 用户体验优化
- 支持DOCX格式

#### 后端任务
- [ ] 实现DOCXProcessor类
- [ ] 优化大文件处理
- [ ] 添加错误日志
- [ ] 实现文档删除功能
- [ ] 添加缓存机制
- [ ] 性能测试

#### 前端任务
- [ ] 优化大文档渲染性能
- [ ] 添加加载动画
- [ ] 优化移动端适配
- [ ] 添加快捷键支持
- [ ] 完善错误提示
- [ ] UI/UX优化

#### 验收标准
- ✅ 支持PDF和DOCX两种格式
- ✅ 大文档处理流畅
- ✅ 用户体验良好
- ✅ 错误提示清晰

---

## 🔍 关键技术验证

### 1. Pix2Text技术验证

**验证目标**：确认Pix2Text能够满足PDF处理需求

**验证方法**：
```python
# test_pix2text.py
from pix2text import Pix2Text

# 初始化
p2t = Pix2Text.from_config()

# 测试PDF处理
result = p2t.recognize_pdf(
    'test.pdf',
    return_text=True,
    rec_config={'formula_ocr': True}
)

print(result['text'])
```

**验证标准**：
- ✅ 能够识别中英文混排文本
- ✅ 能够识别数学公式并转为LaTeX
- ✅ 处理速度可接受（<5秒/页）

---

### 2. Qwen API验证

**验证目标**：确认Qwen API调用正常

**验证方法**：
```python
# test_qwen.py
import os
from dashscope import Generation
import dashscope

# 设置API密钥
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# 测试流式调用
responses = Generation.call(
    model="qwen-plus",
    prompt="介绍一下机器学习",
    stream=True,
    incremental_output=True
)

for response in responses:
    if response.status_code == 200:
        print(response.output.choices[0].message.content, end='')
```

**验证标准**：
- ✅ API密钥有效
- ✅ 流式响应正常
- ✅ 支持长上下文（128k tokens）

---

### 3. 上下文长度测试

**验证目标**：确认长文档的Token管理策略

**验证方法**：
```python
# test_context.py
import tiktoken
from pathlib import Path

encoder = tiktoken.get_encoding("cl100k_base")

# 读取测试PDF转换的Markdown
md_path = Path("test_output.md")
with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

tokens = len(encoder.encode(content))
print(f"Total tokens: {tokens}")

# 测试截断
max_tokens = 120000
if tokens > max_tokens:
    # 实现截断逻辑
    pass
```

**验收标准**：
- ✅ Token计数准确
- ✅ 截断逻辑合理
- ✅ 不破坏文档结构

---

## ⚙️ 环境配置

### 系统环境变量

已确认的环境变量：
```
DASHSCOPE_API_KEY=sk-20b503d6974144118b5f420de1c46bdc
QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### backend/.env

```env
# API配置
API_HOST=127.0.0.1
API_PORT=8000
API_PREFIX=/api/v1

# Qwen配置（从系统环境变量读取）
# DASHSCOPE_API_KEY 已在系统环境变量中配置

# 存储配置
UPLOAD_DIR=./data/uploads
PROCESSED_DIR=./data/processed

# PDF处理选项
USE_MARKER=false

# CORS配置
CORS_ORIGINS=["http://localhost:5173"]

# 日志配置
LOG_LEVEL=INFO
```

---

## 🎨 设计原则与最佳实践

### SOLID原则应用

1. **单一职责原则（SRP）**
   - PDFProcessor只负责PDF处理
   - ContextBuilder只负责上下文管理
   - LLMService只负责LLM调用

2. **开闭原则（OCP）**
   - 通过配置切换Pix2Text/marker-pdf
   - 通过抽象接口支持多种文档类型

3. **里氏替换原则（LSP）**
   - PDFProcessor和DOCXProcessor实现相同接口
   - 可以互换使用

4. **接口隔离原则（ISP）**
   - API端点职责明确
   - 每个模块暴露最小接口

5. **依赖倒置原则（DIP）**
   - 业务逻辑依赖抽象
   - 通过依赖注入管理服务

### 代码规范

- 使用类型提示（Type Hints）
- 使用Pydantic进行数据验证
- 使用async/await处理异步操作
- 完善的错误处理和日志记录
- 单元测试覆盖核心功能

---

## 🧪 测试策略

### 单元测试

```python
# tests/test_pdf_processor.py
import pytest
from app.core.pdf_processor import PDFProcessor

def test_pdf_to_markdown():
    processor = PDFProcessor()
    markdown, images = processor.process(
        "test_data/sample.pdf",
        "test_doc_id",
        "test_output"
    )

    assert markdown is not None
    assert len(markdown) > 0
    assert isinstance(images, list)

# tests/test_llm_service.py
import pytest
from app.core.llm_service import LLMService

@pytest.mark.asyncio
async def test_stream_chat():
    service = LLMService()
    prompt = "介绍一下机器学习"

    chunks = []
    async for chunk in service.stream_chat(prompt):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)
```

### 集成测试

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_document():
    with open("test_data/sample.pdf", "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    assert "doc_id" in response.json()

def test_chat():
    response = client.post(
        "/api/v1/chat/message",
        json={
            "doc_id": "test_doc_id",
            "question": "这篇论文的主要内容是什么？",
            "history": []
        }
    )

    assert response.status_code == 200
```

---

## 📊 性能目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| PDF转换速度 | <5秒/页 | 使用Pix2Text |
| 文档上传 | <10MB支持 | 大部分论文在此范围 |
| AI响应延迟 | <2秒首token | 流式响应 |
| 前端加载时间 | <3秒 | 首屏渲染 |
| 并发支持 | 10个用户 | 本地部署足够 |

---

## ⚠️ 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Pix2Text识别准确率低 | 中 | 中 | 提供marker-pdf升级选项 |
| 文档超出上下文限制 | 中 | 低 | 智能截断策略 |
| Qwen API不稳定 | 高 | 低 | 错误重试机制 |
| 依赖安装困难 | 低 | 中 | 提供Docker方案 |
| Windows兼容性问题 | 中 | 低 | 测试所有依赖 |

---

## 📚 参考资源

### 官方文档
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Pix2Text文档](https://github.com/breezedeus/Pix2Text)
- [PyMuPDF文档](https://pymupdf.readthedocs.io/)
- [Qwen API文档](https://help.aliyun.com/zh/dashscope/)
- [React文档](https://react.dev/)
- [KaTeX文档](https://katex.org/)

### 技术博客
- [Pix2Text实战经验](https://mp.weixin.qq.com/s/...)
- [FastAPI异步最佳实践](https://realpython.com/async-io-python/)
- [React流式UI更新](https://dev.to/...)

---

## ✅ 总结

### 架构优势

1. **简洁高效**
   - 移除向量数据库，降低复杂度
   - 使用Pix2Text，处理速度快
   - 基于上下文问答，实现简单

2. **成本可控**
   - 使用Qwen，性价比高
   - 本地部署，无额外服务器成本
   - 数据隐私安全

3. **易于升级**
   - 保留marker-pdf升级路径
   - 可配置切换LLM
   - 模块化设计，便于扩展

### 预期效果

- ✅ 2周内完成MVP
- ✅ 支持PDF/DOCX格式
- ✅ 准确提取图像和公式
- ✅ 流畅的AI问答体验
- ✅ 友好的用户界面

### 后续迭代方向

1. **功能增强**
   - 支持更多文档格式（EPUB等）
   - 添加文档批注功能
   - 支持文献引用管理

2. **性能优化**
   - 升级到marker-pdf提升质量
   - 引入向量数据库支持长文档
   - 添加缓存机制

3. **用户体验**
   - 移动端适配
   - 多主题支持
   - 快捷键支持

---

**开发计划版本**：v1.0
**创建时间**：2026-01-12
**预计完成时间**：2026-03-12（8周）
**负责人**：开发团队
