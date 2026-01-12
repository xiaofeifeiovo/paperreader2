# PaperReader2 Phase 2 后端实现计划

> **目标**: 实现 PDF 文档的自动处理功能，包括 OCR 识别、公式提取、图像提取和后台异步处理
>
> **开发周期**: 3-5 天
> **优先级**: 高（核心功能）

---

## 🎯 核心目标

### 功能需求
1. **PDF 转 Markdown**: 使用 Pix2Text 进行 OCR 识别，保留文本结构和数学公式
2. **图像提取**: 使用 PyMuPDF 高质量提取 PDF 中的图像
3. **后台处理**: 文档上传后自动触发异步处理，不阻塞 HTTP 响应
4. **状态管理**: 通过文件系统实现状态流转（processing → ready/failed）
5. **错误处理**: 捕获处理异常，生成错误文件，支持前端查询失败原因

### 验收标准
- ✅ 上传 PDF 后自动转为 Markdown（含 LaTeX 公式）
- ✅ 图像正确提取并保存到 `data/processed/images/{doc_id}/`
- ✅ Markdown 中包含图像引用（`![img](/api/v1/documents/{doc_id}/images/img_001)`）
- ✅ 文档列表显示正确状态（processing/ready/failed）
- ✅ 处理失败的文档返回错误信息

### 非功能需求
- **性能**: PDF 处理速度 3-5 秒/页（Pix2Text 基准）
- **可靠性**: 错误不导致服务崩溃，所有异常被捕获
- **可扩展性**: 处理器接口设计支持未来添加 DOCX 支持
- **简单性**: 遵循 KISS、YAGNI 原则，避免过度工程化

---

## 📐 系统架构

### 模块依赖关系

```
app/api/v1/documents.py (API 层)
    ↓ 调用
app/core/document_processor.py (协调层)
    ↓ 使用
app/core/pdf_processor.py (处理层)
    ↓ 依赖
pix2text (OCR + 公式)
pymupdf (图像提取)
```

### 数据流

```
1. 前端上传 PDF
   ↓
2. POST /api/v1/documents/upload
   • 验证文件（格式、大小）
   • 生成 UUID 作为 doc_id
   • 保存到 data/uploads/{doc_id}/original.pdf
   • 添加后台任务到 BackgroundTasks
   • 立即返回 {status: "processing"}
   ↓
3. 后台任务执行 (process_document_background)
   • 初始化 PDFProcessor
   • 调用 processor.process()
   ↓
4. PDFProcessor.process()
   4.1 Pix2Text OCR 识别
       • 输出 Markdown 格式文本
       • 公式转换为 LaTeX ($...$ 和 $$...$$)
   4.2 PyMuPDF 提取图像
       • 遍历所有页面
       • 提取图像并保存
       • 返回图像文件名列表
   4.3 合成最终 Markdown
       • 在 OCR 结果末尾添加图像章节
       • 插入图像引用链接
   ↓
5. 保存处理结果
   • Markdown: data/processed/markdown/{doc_id}.md
   • 图像: data/processed/images/{doc_id}/img_001.png
   ↓
6. 前端轮询查询状态
   GET /api/v1/documents/list
   • 检查 .md 文件存在 → ready
   • 检查 .error 文件存在 → failed
   • 都不存在 → processing
```

### 存储结构

```
data/
├── uploads/                           # 原始上传文件
│   └── {doc_id}/
│       └── original.pdf
│
└── processed/                         # 处理后文件
    ├── markdown/                      # Markdown 文件
    │   ├── {doc_id}.md                # 成功标记
    │   └── {doc_id}.error             # 失败标记 (JSON)
    └── images/                        # 提取的图像
        └── {doc_id}/
            ├── img_001.png
            ├── img_002.png
            └── ...
```

---

## 🔧 实现步骤

### 阶段 1: 创建 PDF 处理器核心

**文件**: `backend/app/core/pdf_processor.py`（新建）

#### 1.1 类结构设计

```python
"""
PDF 文档处理器
使用 Pix2Text 进行 OCR 识别，PyMuPDF 提取图像

职责:
- PDF OCR 识别（文本 + 公式）
- 图像提取和保存
- Markdown 生成和图像引用插入
"""
from typing import Tuple, List
from pathlib import Path
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """文档处理错误基类"""
    pass


class PDFProcessor:
    """PDF 处理器 - Pix2Text + PyMuPDF"""

    def __init__(self):
        """
        初始化处理器

        设计决策:
        - 延迟加载 Pix2Text，避免启动时加载模型（启动时间过长）
        - 使用 @property 惰性初始化
        """
        self._p2t = None

    @property
    def p2t(self):
        """懒加载 Pix2Text 实例"""
        if self._p2t is None:
            from pix2text import Pix2Text
            logger.info("初始化 Pix2Text 模型...")
            self._p2t = Pix2Text.from_config()
            logger.info("Pix2Text 模型初始化完成")
        return self._p2t

    def process(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        处理 PDF 文档（主入口）

        Args:
            pdf_path: PDF 文件绝对路径
            doc_id: 文档唯一 ID
            output_base_dir: 输出基础目录（通常是 data/processed）

        Returns:
            (markdown_content, image_filenames)
            - markdown_content: 完整的 Markdown 文本
            - image_filenames: 图像文件名列表（不含路径和扩展名）

        Raises:
            ProcessingError: 处理失败时抛出

        流程:
        1. OCR 识别 → Markdown 文本
        2. 图像提取 → 图像文件列表
        3. 插入引用 → 最终 Markdown
        """
        logger.info(f"开始处理 PDF: {pdf_path}, doc_id: {doc_id}")

        # 1. OCR 识别
        markdown = self._ocr_with_pix2text(pdf_path)
        logger.info(f"OCR 识别完成，文本长度: {len(markdown)}")

        # 2. 提取图像
        image_filenames = self._extract_images(pdf_path, doc_id, output_base_dir)
        logger.info(f"图像提取完成，共 {len(image_filenames)} 张")

        # 3. 插入图像引用
        final_markdown = self._insert_image_references(markdown, image_filenames, doc_id)

        logger.info(f"PDF 处理完成: {doc_id}")
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
        try:
            logger.info(f"Pix2Text 识别: {pdf_path}")
            result = self.p2t.recognize_pdf(
                pdf_path,
                return_text=True  # 只返回文本，不返回位置信息（更快）
            )
            markdown_content = result['text']
            return markdown_content

        except Exception as e:
            logger.error(f"Pix2Text 识别失败: {e}", exc_info=True)
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
            图像文件名列表（不含路径和扩展名）

        设计决策:
        - 去重: 使用 seen_xrefs 避免重复提取相同图像
        - 命名: 固定格式 img_001.png, img_002.png
        - 保存: PNG 格式（通用性好）
        - 质量: 保持原始质量，不压缩

        Raises:
            ProcessingError: 图像提取失败时抛出
        """
        image_dir = Path(output_base_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        try:
            doc = fitz.open(pdf_path)
            image_filenames = []
            seen_xrefs = set()  # 去重
            img_index = 1

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img in image_list:
                    xref = img[0]  # 图像交叉引用号

                    # 跳过重复图像
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    # 提取图像
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 生成文件名（固定格式）
                    img_filename = f"img_{img_index:03d}"
                    img_path = image_dir / f"{img_filename}.png"

                    # 保存图像
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    image_filenames.append(img_filename)
                    img_index += 1

            doc.close()
            logger.info(f"成功提取 {len(image_filenames)} 张图像")
            return image_filenames

        except Exception as e:
            logger.error(f"图像提取失败: {e}", exc_info=True)
            raise ProcessingError(f"图像提取失败: {str(e)}")

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

        设计决策（MVP 阶段）:
        - 简单策略: 在文档末尾添加所有图像
        - 图像引用格式: ![img_name](/api/v1/documents/{doc_id}/images/img_name)
        - 未来改进: 智能匹配插入位置（基于文本相似度）

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
            # 生成 API 路径（前端可直接访问）
            api_path = f"/api/v1/documents/{doc_id}/images/{img_name}"
            images_section += f"**图 {i}**: ![{img_name}]({api_path})\n\n"

        return markdown + images_section
```

#### 1.2 关键实现细节

**Pix2Text 初始化优化**:
- 延迟加载：首次调用时才初始化模型
- 避免启动时间过长（模型加载需要 3-5 秒）
- 使用 `@property` 实现惰性单例模式

**图像提取去重策略**:
- 使用 `xref`（交叉引用号）作为唯一标识
- PDF 中同一图像可能出现在多页
- `seen_xrefs` 集合避免重复保存

**错误处理策略**:
- 所有异常被捕获并转换为 `ProcessingError`
- 使用 Python `logging` 记录详细错误栈
- 上层调用者可以统一处理错误类型

---

### 阶段 2: 创建后台处理任务

**文件**: `backend/app/core/document_processor.py`（新建）

#### 2.1 后台任务函数设计

```python
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
from typing import Optional

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
```

#### 2.2 关键设计决策

**为什么使用文件系统状态管理？**
- ✅ 简单：无需数据库，减少依赖
- ✅ 可靠：文件存在性原子操作
- ✅ 直观：可直接检查文件状态
- ✅ 符合 KISS 原则

**为什么创建 `.error` 文件？**
- 标记失败状态（无法与其他状态混淆）
- 存储详细错误信息（前端可展示）
- 支持错误分析和调试

**错误文件内容设计**:
```json
{
  "error": "OCR 识别失败: 超时",
  "error_type": "ProcessingError",
  "timestamp": "2026-01-12T18:30:00.123456",
  "doc_id": "abc-123-def",
  "file_path": "data/uploads/abc-123-def/original.pdf",
  "traceback": "Traceback (most recent call last):\n  File ..."
}
```

---

### 阶段 3: 集成后台任务到 API

**文件**: `backend/app/api/v1/documents.py`（修改）

#### 3.1 修改 1: 上传端点添加后台任务

**位置**: 第 48-98 行

```python
# 在文件顶部添加导入
from app.core.document_processor import process_document_background

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None  # 添加参数
) -> DocumentUploadResponse:
    """
    上传文档并启动后台处理

    流程:
    1. 验证文件格式和大小
    2. 生成 doc_id
    3. 保存原始文件
    4. 添加后台处理任务
    5. 立即返回（不等待处理完成）
    """
    # ... 现有验证和保存逻辑（第 58-88 行）保持不变 ...

    # ========== 修改开始 ==========
    # 添加后台处理任务
    if background_tasks:
        background_tasks.add_task(
            process_document_background,
            doc_id=doc_id,
            file_path=str(file_path),
            file_type=file_ext[1:],  # 去掉点号，如 "pdf"
            output_base_dir=str(settings.processed_dir)
        )
    # ========== 修改结束 ==========

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status="processing",  # 从 "uploaded" 改为 "processing"
        message="文档正在处理中",  # 更新提示信息
        file_size=file_size
    )
```

**变更说明**:
1. 添加 `background_tasks` 参数（FastAPI 自动注入）
2. 使用 `background_tasks.add_task()` 添加后台任务
3. 返回状态从 `"uploaded"` 改为 `"processing"`
4. 提示信息更新为"文档正在处理中"

#### 3.2 修改 2: 列表端点完善状态判断

**位置**: 第 101-136 行

```python
@router.get("/list", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    获取所有文档列表

    状态判断逻辑:
    1. 检查 .error 文件 → failed
    2. 检查 .md 文件 → ready
    3. 只有原始文件 → processing
    """
    uploads_dir = settings.upload_dir

    if not uploads_dir.exists():
        return DocumentListResponse(documents=[])

    documents = []
    for doc_dir in uploads_dir.iterdir():
        if doc_dir.is_dir():
            doc_id = doc_dir.name

            # ========== 修改开始 ==========
            # 检查错误文件
            error_file = settings.processed_dir / "markdown" / f"{doc_id}.error"
            if error_file.exists():
                status = "failed"
            else:
                # 检查 Markdown 文件
                md_path = settings.processed_dir / "markdown" / f"{doc_id}.md"
                if md_path.exists():
                    status = "ready"
                else:
                    status = "processing"
            # ========== 修改结束 ==========

            # 获取原始文件信息
            original_files = list(doc_dir.glob("original.*"))
            if original_files:
                original_file = original_files[0]
                stat = original_file.stat()
                documents.append(DocumentInfo(
                    doc_id=doc_id,
                    filename=original_file.name,
                    status=status,  # 使用新的状态逻辑
                    upload_time=stat.st_ctime,
                    file_size=stat.st_size
                ))

    # 按上传时间倒序排序
    documents.sort(key=lambda x: x.upload_time, reverse=True)

    return DocumentListResponse(documents=documents)
```

**变更说明**:
1. 优先检查 `.error` 文件（失败状态优先级最高）
2. 其次检查 `.md` 文件（成功状态）
3. 都不存在则为 `processing` 状态

#### 3.3 修改 3: 获取文档内容返回图像列表

**位置**: 第 139-160 行

```python
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
    # ========== 修改开始 ==========
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
        "images": images,  # 新增：图像列表
        "status": "ready"
    }
    # ========== 修改结束 ==========
```

**变更说明**:
1. 添加错误文件检查（读取并返回错误信息）
2. 添加图像列表获取逻辑
3. 返回结果中包含 `images` 字段

---

### 阶段 4: 添加单元测试

**文件**: `backend/tests/test_pdf_processor.py`（新建）

#### 4.1 测试结构

```python
"""
PDF 处理器单元测试
"""
import pytest
from pathlib import Path
from app.core.pdf_processor import PDFProcessor, ProcessingError


class TestPDFProcessor:
    """PDF 处理器测试套件"""

    def test_init(self):
        """测试初始化"""
        processor = PDFProcessor()
        assert processor._p2t is None  # 未加载

    def test_lazy_loading(self):
        """测试惰性加载"""
        processor = PDFProcessor()
        # 首次访问属性时才加载
        _ = processor.p2t
        assert processor._p2t is not None

    @pytest.mark.parametrize("pdf_file", [
        "tests/fixtures/sample.pdf",
        "tests/fixtures/with_formulas.pdf"
    ])
    def test_ocr_with_pix2text(self, pdf_file):
        """测试 Pix2Text OCR 功能"""
        processor = PDFProcessor()

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        markdown = processor._ocr_with_pix2text(pdf_file)

        # 验证返回值
        assert isinstance(markdown, str)
        assert len(markdown) > 0

        # 验证 Markdown 格式（包含标题或公式）
        assert "#" in markdown or "$" in markdown

    def test_extract_images(self, tmp_path):
        """测试图像提取功能"""
        processor = PDFProcessor()
        pdf_file = "tests/fixtures/with_images.pdf"

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        images = processor._extract_images(
            pdf_file, "test_doc", str(tmp_path)
        )

        # 验证返回值
        assert isinstance(images, list)

        # 验证文件存在
        for img_name in images:
            img_path = tmp_path / "images" / "test_doc" / f"{img_name}.png"
            assert img_path.exists()

    def test_process_full(self, tmp_path):
        """测试完整处理流程"""
        processor = PDFProcessor()
        pdf_file = "tests/fixtures/sample.pdf"

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        markdown, images = processor.process(
            pdf_file, "test_doc", str(tmp_path)
        )

        # 验证返回值
        assert markdown is not None
        assert len(markdown) > 0
        assert isinstance(images, list)

        # 验证 Markdown 包含图像引用
        if images:
            assert "![img_" in markdown
            assert "/api/v1/documents/" in markdown

    def test_error_handling(self):
        """测试错误处理"""
        processor = PDFProcessor()

        with pytest.raises(ProcessingError):
            processor._ocr_with_pix2text("nonexistent.pdf")
```

#### 4.2 测试数据准备

创建测试文件目录：
```
backend/tests/fixtures/
├── sample.pdf              # 普通 PDF（文本）
├── with_images.pdf         # 含图像的 PDF
├── with_formulas.pdf       # 含公式的 PDF
└── corrupted.pdf           # 损坏的 PDF（用于错误测试）
```

---

**文件**: `backend/tests/test_api.py`（新建）

```python
"""
API 集成测试
"""
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestDocumentAPI:
    """文档 API 测试套件"""

    def test_upload_document(self):
        """测试文档上传"""
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "doc_id" in data
        assert data["status"] == "processing"

        return data["doc_id"]

    def test_upload_invalid_format(self):
        """测试上传不支持的格式"""
        with open("tests/fixtures/sample.txt", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )

        assert response.status_code == 400

    def test_list_documents(self):
        """测试文档列表"""
        response = client.get("/api/v1/documents/list")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_upload_and_process(self):
        """测试上传和处理完整流程"""
        # 1. 上传文档
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        doc_id = response.json()["doc_id"]

        # 2. 等待处理完成（最多 60 秒）
        max_wait = 60
        start = time.time()

        while time.time() - start < max_wait:
            response = client.get(f"/api/v1/documents/{doc_id}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ready":
                    break

            time.sleep(2)

        # 3. 验证最终结果
        final_response = client.get(f"/api/v1/documents/{doc_id}")
        assert final_response.status_code == 200
        data = final_response.json()

        assert "content" in data
        assert len(data["content"]) > 0
        assert "images" in data
        assert isinstance(data["images"], list)
```

---

## 🗂️ 文件清单

### 需要创建的文件

| 文件路径 | 说明 | 代码行数（估计） |
|---------|------|----------------|
| `backend/app/core/pdf_processor.py` | PDF 处理器核心 | ~150 行 |
| `backend/app/core/document_processor.py` | 后台任务协调器 | ~80 行 |
| `backend/tests/test_pdf_processor.py` | 单元测试 | ~120 行 |
| `backend/tests/test_api.py` | API 集成测试 | ~100 行 |
| `backend/tests/fixtures/.gitkeep` | 测试数据目录 | 1 行 |

**总计**: ~450 行新代码

### 需要修改的文件

| 文件路径 | 修改内容 | 修改行数 |
|---------|---------|---------|
| `backend/app/api/v1/documents.py` | 添加后台任务、完善状态判断、返回图像列表 | ~30 行 |
| `backend/app/config.py` | 验证配置（可能无需修改） | 0 行 |

**总计**: ~30 行修改

### 可能需要补充的依赖

检查 `requirements.txt`，确认以下依赖存在：
```
pix2text>=1.1.0           # ✅ 已存在
pymupdf==1.23.8           # ✅ 已存在
python-docx==1.1.0        # ✅ 已存在（暂不使用）
pytest>=7.4.0             # ✅ 已存在
```

**结论**: 无需新增依赖

---

## 🎨 架构原则应用

### SOLID 原则

#### 单一职责原则（SRP）
- `PDFProcessor`: 只负责 PDF 处理，不涉及 API 和存储
- `document_processor.py`: 只负责任务协调，不涉及具体处理逻辑
- `documents.py`: 只负责 HTTP 请求响应，不涉及处理细节

#### 开闭原则（OCP）
- `PDFProcessor` 接口设计支持未来扩展 `DOCXProcessor`
- 通过文件类型判断选择处理器（易于添加新类型）
- 处理器统一接口 `process()` 方法

#### 里氏替换原则（LSP）
- 未来 `DOCXProcessor` 可完全替换 `PDFProcessor`
- 两者实现相同的接口契约

#### 接口隔离原则（ISP）
- API 端点职责明确（上传、列表、详情、删除）
- 避免臃肿的接口（每个端点只做一件事）

#### 依赖倒置原则（DIP）
- `document_processor.py` 依赖处理器抽象，不依赖具体实现
- API 层依赖后台任务抽象，不依赖具体处理器

### KISS 原则（Keep It Simple, Stupid）

**简单性体现**:
1. ✅ **状态管理**: 使用文件系统而非数据库
2. ✅ **任务队列**: 使用 FastAPI BackgroundTasks 而非 Celery
3. ✅ **图像引用**: 在文档末尾添加而非智能匹配
4. ✅ **错误处理**: 文件标记而非复杂状态机

**复杂度权衡**:
- 当前方案: 文件系统状态 + BackgroundTasks
- 备选方案: Redis + Celery（过度工程，YAGNI）

### YAGNI 原则（You Aren't Gonna Need It）

**功能取舍**:
1. ❌ **暂不实现**: DOCX 支持（Phase 4 再考虑）
2. ❌ **暂不实现**: 任务进度回调（MVP 不需要）
3. ❌ **暂不实现**: 对话历史持久化（Phase 3）
4. ❌ **暂不实现**: 分布式任务队列（单机部署够用）

**保留核心功能**:
- ✅ PDF OCR 和图像提取
- ✅ 后台异步处理
- ✅ 状态查询

### DRY 原则（Don't Repeat Yourself）

**代码复用**:
1. ✅ **统一处理器接口**: `process(file_path, doc_id, output_dir)`
2. ✅ **统一错误处理**: `ProcessingError` 基类
3. ✅ **统一文件命名**: `{doc_id}.md`, `{doc_id}.error`
4. ✅ **统一路径生成**: `Path(output_dir) / "markdown" / f"{doc_id}.md"`

**避免重复**:
- 状态判断逻辑封装在 API 层（不散落各处）
- 日志记录使用统一格式

---

## ⚠️ 风险分析和缓解策略

### 风险 1: Pix2Text 性能问题

**风险描述**:
- OCR 识别速度慢（>5 秒/页）
- 大文件处理时间过长（用户等待）

**影响范围**: 用户体验

**缓解策略**:
1. **配置优化**: 使用轻量级模型
   ```python
   self.p2t = Pix2Text.from_config(
       formula_config={'model_name': 'mfr'}  # 更快的模型
   )
   ```

2. **分页处理**: 支持进度回调（未来改进）
   ```python
   def process_with_progress(pdf_path, callback):
       for page in pages:
           process_page(page)
           callback(progress, total)
   ```

3. **异步处理**: ✅ 已实现（BackgroundTasks）
   - 用户无需等待，立即返回
   - 前端轮询查询状态

### 风险 2: 内存溢出

**风险描述**:
- 处理大 PDF（>100 页）时内存不足
- 同时处理多个文档导致资源耗尽

**影响范围**: 服务稳定性

**缓解策略**:
1. **限制并发任务**: 使用信号量
   ```python
   import asyncio
   MAX_CONCURRENT_TASKS = 3
   semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

   async def process_with_limit(...):
       async with semaphore:
           await process_document_background(...)
   ```

2. **分块处理**: 逐页处理而非一次性加载
   ```python
   def process_large_pdf(pdf_path):
       doc = fitz.open(pdf_path)
       for page in doc:
           process_page(page)
       ```

3. **临时文件**: 使用文件而非内存存储中间结果
   ```python
   with tempfile.NamedTemporaryFile() as f:
       f.write(intermediate_result)
   ```

### 风险 3: Pix2Text 安装失败

**风险描述**:
- PyTorch 依赖复杂
- Windows 环境兼容性问题

**影响范围**: 环境搭建

**缓解策略**:
1. **详细安装指南**:
   ```bash
   # Windows 安装脚本
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   pip install pix2text
   ```

2. **环境检查脚本**:
   ```python
   # check_env.py
   def check_dependencies():
       try:
           import torch
           import pix2text
           import fitz
           print("✅ 所有依赖已安装")
       except ImportError as e:
           print(f"❌ 缺少依赖: {e}")
   ```

3. **Docker 容器化**（备选方案）:
   ```dockerfile
   FROM python:3.11-slim
   RUN pip install torch pix2text pymupdf fastapi
   WORKDIR /app
   CMD ["python", "-m", "app.main"]
   ```

### 风险 4: OCR 准确率低

**风险描述**:
- 公式识别错误
- 复杂布局解析失败

**影响范围**: 输出质量

**缓解策略**:
1. **备选方案**: marker-pdf（配置切换）
   ```python
   if settings.use_marker:
       from marker.convert import convert_single_pdf
       markdown = convert_single_pdf(pdf_path)
   ```

2. **用户反馈**: 收集错误案例，持续优化

3. **人工审核**: MVP 阶段允许用户手动修正

---

## ✅ 验收检查清单

### 功能验收

- [ ] **上传功能**: 上传 PDF 后立即返回 `{status: "processing"}`
- [ ] **OCR 识别**: Markdown 包含正确的文本和结构
- [ ] **公式识别**: LaTeX 公式格式正确（`$E=mc^2$`）
- [ ] **图像提取**: 所有图像保存到 `data/processed/images/{doc_id}/`
- [ ] **图像引用**: Markdown 中包含图像链接（`![img](/api/v1/...)`）
- [ ] **状态管理**: 列表显示正确状态（processing/ready/failed）
- [ ] **错误处理**: 失败文档显示 `failed` 状态和错误信息
- [ ] **文档详情**: `GET /documents/{doc_id}` 返回图像列表

### 性能验收

- [ ] **处理速度**: 10 页 PDF 处理时间 <60 秒
- [ ] **响应时间**: 上传接口 <500ms（不包含处理时间）
- [ ] **并发支持**: 同时处理 3 个文档不崩溃

### 测试验收

- [ ] **单元测试**: `pytest tests/test_pdf_processor.py` 全部通过
- [ ] **API 测试**: `pytest tests/test_api.py` 全部通过
- [ ] **测试覆盖率**: >80%（使用 `pytest --cov=app`）

### 文档验收

- [ ] **代码注释**: 所有公共方法有 docstring
- [ ] **日志记录**: 关键步骤有日志输出
- [ ] **错误信息**: 错误文件包含详细 trace

---

## 🚀 开发时间线

### 第 1 天：PDF 处理器核心
- **上午**: 创建 `pdf_processor.py`，实现 OCR 识别
- **下午**: 实现图像提取和 Markdown 合成
- **验收**: 使用测试 PDF 验证输出正确

### 第 2 天：后台任务和 API 集成
- **上午**: 创建 `document_processor.py`，实现后台任务
- **下午**: 修改 `documents.py`，集成后台任务
- **验收**: 上传 PDF 后自动处理，状态正确更新

### 第 3 天：测试和优化
- **上午**: 编写单元测试（`test_pdf_processor.py`）
- **下午**: 编写 API 测试（`test_api.py`）
- **验收**: 所有测试通过，覆盖率 >80%

### 第 4-5 天：（可选）优化和完善
- 性能优化（并发限制、内存管理）
- 错误处理完善
- 日志和文档补充

---

## 📚 参考资源

### 官方文档
- **Pix2Text**: https://github.com/Byaidu/Pix2Text
- **PyMuPDF**: https://pymupdf.readthedocs.io/
- **FastAPI BackgroundTasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/

### 项目文档
- **后端文档**: `backend/CLAUDE.md`
- **项目文档**: `CLAUDE.md`
- **开发计划**: `devplan.md`

### 技术参考
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **Python logging**: https://docs.python.org/3/library/logging.html

---

## 📝 附录

### A. 错误文件示例

```json
{
  "error": "OCR 识别失败: Pix2Text 识别超时",
  "error_type": "ProcessingError",
  "timestamp": "2026-01-12T18:30:45.123456",
  "doc_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_path": "data/uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890/original.pdf",
  "traceback": "Traceback (most recent call last):\n  File \"app/core/pdf_processor.py\", line 85, in _ocr_with_pix2text\n    result = self.p2t.recognize_pdf(pdf_path, return_text=True)\nTimeoutError: Pix2Text recognition timeout\n"
}
```

### B. Markdown 输出示例

```markdown
# 深度学习在自然语言处理中的应用

## 摘要
本文介绍了深度学习技术在NLP领域的应用...

## 方法

我们使用的模型基于Transformer架构：

$$
Attention(Q, K, V) = softmax(\frac{QK^T}{\sqrt{d_k}})V
$$

## 实验

实验结果如下表所示：

| 模型 | 准确率 | 召回率 |
|------|--------|--------|
| BERT | 92.5% | 89.3% |
| GPT-3 | 94.1% | 91.2% |

## 文档图像

**图 1**: ![img_001](/api/v1/documents/a1b2c3d4/images/img_001)

**图 2**: ![img_002](/api/v1/documents/a1b2c3d4/images/img_002)
```

### C. API 响应示例

**上传响应**:
```json
{
  "doc_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "paper.pdf",
  "status": "processing",
  "message": "文档正在处理中",
  "file_size": 1234567
}
```

**文档列表响应**:
```json
{
  "documents": [
    {
      "doc_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "filename": "original.pdf",
      "status": "ready",
      "upload_time": 1705053600.0,
      "file_size": 1234567
    },
    {
      "doc_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "filename": "another.pdf",
      "status": "processing",
      "upload_time": 1705053660.0,
      "file_size": 987654
    },
    {
      "doc_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
      "filename": "failed.pdf",
      "status": "failed",
      "upload_time": 1705053720.0,
      "file_size": 500000
    }
  ]
}
```

**文档详情响应**:
```json
{
  "doc_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "content": "# 论文标题\n\n...",
  "images": ["img_001", "img_002", "img_003"],
  "status": "ready"
}
```

---

**计划版本**: 1.0
**创建日期**: 2026-01-12
**作者**: Claude Code
**项目**: PaperReader2 Phase 2 - 后端开发
