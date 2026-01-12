# Phase 2: Marker PDF转换器支持 - 实施计划

## 📋 项目概述

### 目标
在PaperReader2中集成marker-pdf作为可选的PDF转换器，用户可以通过前端下拉菜单选择使用Pix2Text或Marker进行PDF转Markdown处理。

### 用户决策确认
- ✅ **功能启用**: 立即启用完整功能
- ✅ **UI设计**: 下拉菜单选择器
- ✅ **元数据保存**: 仅在响应message中提示，不保存到文档模型

---

## 🔍 技术背景分析

### Marker PDF特性

**优势**：
- 高精度布局识别（复杂表格、多栏排版）
- 自动提取图像和公式
- 支持10+种文件格式
- 速度比Nougat快10倍

**性能指标**（来自测试数据）：
| 指标 | Pix2Text | Marker |
|------|----------|--------|
| 速度 | 3-5秒/页 | 8-15秒/页 |
| GPU内存 | ~500MB | ~4-5GB |
| 布局识别 | 标准 | 高 |
| 表格还原 | 良好 | 优秀 |
| 公式识别 | 优秀 | 良好 |

**系统要求**：
- Python 3.10+
- PyTorch 2.7.0+
- GPU VRAM: 5GB最低，8GB推荐
- 系统RAM: 8GB最低，16GB推荐

### Marker输出格式

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

converter = PdfConverter(artifact_dict=create_model_dict())
rendered = converter("input.pdf")  # 返回Pydantic模型

# 提取Markdown和图像
markdown, _, images = text_from_rendered(rendered)
# markdown: str - 完整的Markdown文本
# images: dict - {image_id: PIL.Image对象}
```

**关键差异**：
1. Marker返回`images`字典（PIL.Image对象），需要手动保存
2. Markdown中可能包含相对路径图像引用，需要转换为API路径
3. 生成的Markdown格式与Pix2Text兼容

### 潜在问题分析

**问题1：GPU内存冲突**
- Pix2Text和Marker都需要GPU内存
- 同时加载会导致OOM
- **解决方案**：懒加载隔离 + 按需初始化

**问题2：依赖安装复杂**
- marker-pdf需要PyTorch和其他深度学习依赖
- Python 3.13/3.14有兼容性问题
- **解决方案**：可选依赖 + 优雅降级

**问题3：图像路径不统一**
- Marker生成的图像引用可能是相对路径
- 前端无法直接访问
- **解决方案**：后处理转换图像路径

---

## 🏗️ 架构设计

### 设计模式：策略模式（Strategy Pattern）

```
┌─────────────────────────────────────────────┐
│         前端 FileUpload 组件                │
│  ┌─────────────────────────────────────┐   │
│  │ <select> 选择转换器                │   │
│  │  • Pix2Text (快速，推荐)           │   │
│  │  • Marker (高质量，慢)             │   │
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │ FormData: file + converter
                  ↓
┌─────────────────────────────────────────────┐
│   POST /api/v1/documents/upload             │
│   接收converter参数（默认pix2text）          │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│   process_document_background()             │
│   根据converter参数选择处理器                │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│         PDFProcessor (门面类)                │
│   动态加载转换器，确保懒加载隔离             │
└─────────────────┬───────────────────────────┘
          ┌────────┴────────┐
          ↓                 ↓
┌─────────────────┐  ┌─────────────────┐
│ Pix2TextConverter│  │ MarkerConverter │
│  • OCR识别       │  │  • 高精度布局   │
│  • 公式转换      │  │  • 表格还原     │
│  • ~500MB VRAM   │  │  • ~5GB VRAM    │
└─────────────────┘  └─────────────────┘
          └────────┬────────┘
                   ↓
        ┌──────────────────┐
        │  统一输出格式     │
        │  • Markdown文本   │
        │  • 图像文件列表   │
        │  • API路径引用    │
        └──────────────────┘
```

### 核心设计原则

**1. 懒加载隔离（Lazy Loading Isolation）**
```python
class PDFProcessor:
    def __init__(self, converter: str, device: str):
        self.converter_name = converter
        self.device = device
        self._converter_impl = None  # 延迟初始化，避免同时加载

    @property
    def converter_impl(self):
        if self._converter_impl is None:
            self._converter_impl = self._load_converter()
        return self._converter_impl
```

**2. 优雅降级（Graceful Degradation）**
```python
def _load_converter(self, name: str):
    try:
        if name == "marker":
            import marker  # 检查依赖
            return MarkerConverter(self.device)
    except ImportError:
        logger.warning("⚠️ marker未安装，自动降级到pix2text")
        return Pix2TextConverter(self.device)
```

**3. 统一输出接口（Unified Interface）**
```python
class PDFConverterBase(ABC):
    @abstractmethod
    def convert_to_markdown(
        self, pdf_path: str, doc_id: str, output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """返回 (markdown_content, image_filenames)"""
        pass
```

---

## 📁 文件修改清单

### 后端（8个文件）

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `backend/requirements.txt` | 修改 | 添加marker-pdf依赖 |
| `backend/app/core/converters/__init__.py` | 新建 | 模块初始化 |
| `backend/app/core/converters/base.py` | 新建 | 转换器抽象基类 |
| `backend/app/core/converters/pix2text_converter.py` | 新建 | Pix2Text实现（迁移现有代码） |
| `backend/app/core/converters/marker_converter.py` | 新建 | Marker实现 |
| `backend/app/core/pdf_processor.py` | 修改 | 重构为门面类 |
| `backend/app/core/document_processor.py` | 修改 | 传递converter参数 |
| `backend/app/api/v1/documents.py` | 修改 | 接收converter参数 |
| `backend/app/models/document.py` | 新建或修改 | ConverterType枚举 |

### 前端（4个文件）

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `frontend/src/types/document.ts` | 修改 | 添加ConverterType类型和常量 |
| `frontend/src/services/document.ts` | 修改 | uploadDocument添加converter参数 |
| `frontend/src/store/documentStore.ts` | 修改 | 传递converter参数 |
| `frontend/src/components/FileUpload.tsx` | 修改 | 添加下拉菜单选择器 |

---

## 🚀 详细实施步骤

### 阶段1：后端核心（3-4小时）

#### 步骤1.1：添加依赖
**文件**: `backend/requirements.txt`

```diff
# PDF处理
pix2text>=1.1.0           # 主要方案:OCR + 公式识别
pymupdf==1.23.8           # 图像提取
- # marker-pdf>=0.2.6       # 升级选项(注释,按需启用)
+ marker-pdf>=0.2.6       # 高精度PDF转Markdown
```

**安装命令**：
```bash
cd backend
pip install marker-pdf>=0.2.6
```

#### 步骤1.2：创建转换器基类
**文件**: `backend/app/core/converters/base.py`（新建）

```python
"""
PDF转换器抽象基类
定义统一的转换器接口，确保所有转换器实现具有相同的签名和行为
"""
from abc import ABC, abstractmethod
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class PDFConverterBase(ABC):
    """
    PDF转换器抽象基类

    所有PDF转换器必须实现此接口，确保：
    1. 统一的输入输出格式
    2. 一致的错误处理方式
    3. 兼容的图像引用格式
    """

    def __init__(self, device: str = "auto"):
        """
        初始化转换器

        Args:
            device: 设备类型 ('cuda', 'cpu', 'auto')
        """
        self.device = device
        logger.info(f"📦 初始化转换器: {self.__class__.__name__}, device={device}")

    @abstractmethod
    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        将PDF转换为Markdown

        Args:
            pdf_path: PDF文件绝对路径
            doc_id: 文档唯一ID
            output_base_dir: 输出基础目录（通常是 data/processed）

        Returns:
            (markdown_content, image_filenames)
            - markdown_content: 完整的Markdown文本
            - image_filenames: 图像文件名列表（不含路径和扩展名）

        Raises:
            ProcessingError: 转换失败时抛出

        注意:
            - 图像应保存到 {output_base_dir}/images/{doc_id}/
            - 图像命名格式: img_001.png, img_002.png, ...
            - Markdown中的图像引用应使用API路径格式
        """
        pass

    def get_converter_name(self) -> str:
        """获取转换器名称"""
        return self.__class__.__name__
```

#### 步骤1.3：实现Pix2Text转换器
**文件**: `backend/app/core/converters/pix2text_converter.py`（新建）

```python
"""
Pix2Text PDF转换器实现
从现有pdf_processor.py迁移代码，保持功能完全一致
"""
import logging
from typing import Tuple, List
from pathlib import Path
from .base import PDFConverterBase

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """处理错误基类"""
    pass


class Pix2TextConverter(PDFConverterBase):
    """
    Pix2Text转换器

    特点:
    - 快速OCR识别（3-5秒/页）
    - 优秀的公式识别能力
    - 适合学术论文和技术文档

    资源占用:
    - GPU VRAM: ~500MB
    - 系统RAM: ~1GB
    """

    def __init__(self, device: str = "auto"):
        super().__init__(device)
        self._p2t = None

    @property
    def p2t(self):
        """懒加载Pix2Text实例（复用现有逻辑）"""
        if self._p2t is None:
            from pix2text import Pix2Text
            logger.info(f"⏳ 正在初始化Pix2Text模型 (device={self.device})...")

            try:
                self._p2t = Pix2Text.from_config(
                    enable_formula=True,
                    enable_table=True,
                    device=self.device
                )
                logger.info(f"✅ Pix2Text模型初始化完成")

            except ValueError as e:
                if 'CUDAExecutionProvider' in str(e) and self.device == 'cuda':
                    logger.warning(f"🔄 GPU初始化失败，降级到CPU...")
                    self.device = 'cpu'
                    self._p2t = Pix2Text.from_config(
                        enable_formula=True,
                        enable_table=True,
                        device='cpu'
                    )
                else:
                    raise ProcessingError(f"Pix2Text初始化失败: {e}")

        return self._p2t

    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """使用Pix2Text进行PDF转换（完全迁移现有逻辑）"""
        import time
        from pathlib import Path

        process_start = time.time()
        logger.info(f"🚀 [Pix2Text] 开始转换: doc_id={doc_id}")

        # 1. OCR识别（迁移现有代码）
        ocr_start = time.time()
        markdown = self._ocr_with_pix2text(pdf_path)
        ocr_time = time.time() - ocr_start
        logger.info(f"✅ [Pix2Text] OCR完成: time={ocr_time:.2f}s")

        # 2. 提取图像（迁移现有代码）
        extract_start = time.time()
        image_filenames = self._extract_images(pdf_path, doc_id, output_base_dir)
        extract_time = time.time() - extract_start
        logger.info(f"✅ [Pix2Text] 图像提取: count={len(image_filenames)}, time={extract_time:.2f}s")

        # 3. 插入图像引用（迁移现有代码）
        final_markdown = self._insert_image_references(markdown, image_filenames, doc_id)

        total_time = time.time() - process_start
        logger.info(f"🎉 [Pix2Text] 转换完成: time={total_time:.2f}s")

        return final_markdown, image_filenames

    # 以下方法完全迁移现有pdf_processor.py的代码
    # _ocr_with_pix2text()
    # _extract_images()
    # _insert_image_references()
```

**迁移说明**：
- 从`backend/app/core/pdf_processor.py`复制三个私有方法
- 保持所有日志记录和错误处理逻辑
- 修改日志前缀为`[Pix2Text]`

#### 步骤1.4：实现Marker转换器
**文件**: `backend/app/core/converters/marker_converter.py`（新建）

```python
"""
Marker PDF转换器实现
高精度布局识别和表格还原
"""
import logging
import re
from typing import Tuple, List
from pathlib import Path
from .base import PDFConverterBase

logger = logging.getLogger(__name__)


class MarkerConverter(PDFConverterBase):
    """
    Marker转换器

    特点:
    - 高精度布局识别（适合复杂文档）
    - 优秀的表格还原能力
    - 自动图像提取

    资源占用:
    - GPU VRAM: ~4-5GB
    - 系统RAM: ~2GB

    性能:
    - 速度: 8-15秒/页（比Pix2Text慢2-3倍）
    - 质量: 更适合复杂布局和表格密集文档
    """

    def __init__(self, device: str = "auto"):
        super().__init__(device)
        self._converter = None

    @property
    def converter(self):
        """懒加载Marker实例"""
        if self._converter is None:
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict

                logger.info(f"⏳ 正在初始化Marker模型 (device={self.device})...")

                # Marker自动检测设备，不需要手动指定
                self._converter = PdfConverter(
                    artifact_dict=create_model_dict(),
                )

                logger.info(f"✅ Marker模型初始化完成")

            except ImportError as e:
                logger.error(f"❌ Marker未安装: {e}")
                raise ImportError(
                    "marker-pdf未安装，请运行: pip install marker-pdf>=0.2.6"
                )
            except Exception as e:
                logger.error(f"❌ Marker初始化失败: {e}", exc_info=True)
                raise

        return self._converter

    def convert_to_markdown(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """使用Marker进行PDF转换"""
        import time

        process_start = time.time()
        pdf_name = Path(pdf_path).name
        logger.info(f"🚀 [Marker] 开始转换: doc_id={doc_id}, file='{pdf_name}'")

        try:
            # 1. 调用Marker进行转换
            convert_start = time.time()
            rendered = self.converter(pdf_path)
            convert_time = time.time() - convert_start
            logger.info(f"✅ [Marker] 转换完成: time={convert_time:.2f}s")

            # 2. 提取文本和图像
            from marker.output import text_from_rendered
            extract_start = time.time()
            markdown, _, images = text_from_rendered(rendered)
            extract_time = time.time() - extract_start

            logger.info(
                f"📝 [Marker] 内容提取: "
                f"markdown_size={len(markdown)}, "
                f"images={len(images)}, "
                f"time={extract_time:.2f}s"
            )

            # 3. 保存Marker提取的图像
            save_start = time.time()
            image_filenames = self._save_marker_images(images, doc_id, output_base_dir)
            save_time = time.time() - save_start
            logger.info(f"💾 [Marker] 图像保存: count={len(image_filenames)}, time={save_time:.2f}s")

            # 4. 处理Markdown中的图像引用（转换为API路径）
            markdown = self._process_image_references(markdown, image_filenames, doc_id)

            total_time = time.time() - process_start
            logger.info(
                f"🎉 [Marker] 转换成功: "
                f"doc_id={doc_id}, "
                f"total_time={total_time:.2f}s, "
                f"markdown_size={len(markdown)}, "
                f"images={len(image_filenames)}"
            )

            return markdown, image_filenames

        except Exception as e:
            logger.error(f"❌ [Marker] 转换失败: {e}", exc_info=True)
            raise ProcessingError(f"Marker转换失败: {str(e)}")

    def _save_marker_images(
        self,
        images: dict,
        doc_id: str,
        output_base_dir: str
    ) -> List[str]:
        """
        保存Marker提取的图像

        Args:
            images: Marker返回的图像字典 {image_id: PIL.Image}
            doc_id: 文档ID
            output_base_dir: 输出目录

        Returns:
            图像文件名列表（不含路径和扩展名）
        """
        image_dir = Path(output_base_dir) / "images" / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)

        image_filenames = []
        for idx, (img_id, img_pil) in enumerate(images.items(), 1):
            img_filename = f"img_{idx:03d}"
            img_path = image_dir / f"{img_filename}.png"

            # 保存为PNG格式
            img_pil.save(img_path, "PNG")
            image_filenames.append(img_filename)

            # 图像保存日志
            try:
                width, height = img_pil.size
                logger.info(
                    f"🖼️ [Marker] 图像保存: "
                    f"img_{idx:03d}, "
                    f"size={width}x{height}, "
                    f"format=PNG, "
                    f"mode={img_pil.mode}"
                )
            except Exception as e:
                logger.debug(f"⚠️ [Marker] 图像元数据获取失败: {e}")

        return image_filenames

    def _process_image_references(
        self,
        markdown: str,
        image_filenames: List[str],
        doc_id: str
    ) -> str:
        """
        处理Markdown中的图像引用

        Marker可能使用相对路径或绝对路径，需要统一转换为API路径格式
        """
        # Marker生成的图像引用格式可能为：
        # - ![](img_001.png)
        # - ![](./img_001.png)
        # - ![](images/img_001.png)
        # 或其他变体

        for img_name in image_filenames:
            api_path = f"/api/v1/documents/{doc_id}/images/{img_name}"

            # 替换所有可能的引用格式
            patterns = [
                rf'!\[.*?\]\({img_name}\)',          # ![](img_001.png)
                rf'!\[.*?\]\(\./{img_name}\)',       # ![](./img_001.png)
                rf'!\[.*?\]\(images/{img_name}\)',   # ![](images/img_001.png)
                rf'!\[.*?\]\(\./images/{img_name}\)', # ![](./images/img_001.png)
            ]

            for pattern in patterns:
                markdown = re.sub(pattern, f'![{img_name}]({api_path})', markdown)

        logger.debug(f"🔗 [Marker] 图像引用处理完成: count={len(image_filenames)}")
        return markdown
```

#### 步骤1.5：重构PDFProcessor为门面类
**文件**: `backend/app/core/pdf_processor.py`（修改）

```python
"""
PDF处理器 - 门面类（Facade Pattern）
根据converter参数动态选择具体转换器实现
"""
from typing import Tuple, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """智能检测最佳设备（保持现有逻辑不变）"""
    # ... 完全保留现有代码 ...
    pass


class ProcessingError(Exception):
    """处理错误基类"""
    pass


class PDFProcessor:
    """
    PDF处理器门面类

    职责:
    - 根据converter参数选择具体转换器
    - 提供统一的处理接口
    - 确保懒加载隔离，避免同时加载多个转换器

    设计模式:
    - 门面模式（Facade）：隐藏转换器实现细节
    - 策略模式（Strategy）：动态选择转换器算法
    """

    # 转换器映射表
    CONVERTERS = {
        "pix2text": "app.core.converters.pix2text_converter.Pix2TextConverter",
        "marker": "app.core.converters.marker_converter.MarkerConverter",
    }

    def __init__(self, converter: str = "pix2text", device: Optional[str] = None):
        """
        初始化处理器

        Args:
            converter: 转换器名称 ("pix2text" 或 "marker")
            device: 设备类型 ("cuda", "cpu", "auto")，None表示自动检测

        Raises:
            ValueError: 不支持的转换器
        """
        self.converter_name = converter
        self.device = device or detect_device()
        self._converter_impl = None  # 延迟加载，避免同时初始化

        logger.info(
            f"📦 PDFProcessor初始化: "
            f"converter={converter}, "
            f"device={self.device}"
        )

    @property
    def converter_impl(self):
        """
        懒加载转换器实现

        延迟加载的好处:
        1. 避免启动时同时加载多个模型（节省内存）
        2. 只加载用户选择的转换器
        3. 加快启动速度
        """
        if self._converter_impl is None:
            self._converter_impl = self._load_converter(self.converter_name)
        return self._converter_impl

    def _load_converter(self, converter_name: str):
        """
        动态加载转换器类

        Args:
            converter_name: 转换器名称

        Returns:
            转换器实例

        Raises:
            ValueError: 不支持的转换器
            ImportError: 转换器依赖未安装
        """
        if converter_name not in self.CONVERTERS:
            raise ValueError(
                f"❌ 不支持的转换器: {converter_name}. "
                f"支持的转换器: {list(self.CONVERTERS.keys())}"
            )

        # 动态导入转换器模块
        module_path = self.CONVERTERS[converter_name]
        try:
            module = __import__(module_path, fromlist=[""])

            # 获取转换器类名（如 Pix2TextConverter）
            class_name = converter_name.title().replace("_", "") + "Converter"
            converter_class = getattr(module, class_name)

            # 实例化转换器
            instance = converter_class(device=self.device)

            logger.info(f"✅ 转换器加载成功: {class_name}")
            return instance

        except ImportError as e:
            # 优雅降级：如果marker未安装，降级到pix2text
            if converter_name == "marker":
                logger.warning(
                    f"⚠️ marker-pdf未安装，自动降级到pix2text。"
                    f"安装命令: pip install marker-pdf>=0.2.6"
                )
                logger.warning(f"   详细错误: {e}")
                # 递归加载pix2text
                return self._load_converter("pix2text")
            else:
                logger.error(f"❌ 转换器加载失败: {e}", exc_info=True)
                raise ProcessingError(
                    f"转换器 {converter_name} 加载失败: {str(e)}"
                )

    def process(
        self,
        pdf_path: str,
        doc_id: str,
        output_base_dir: str
    ) -> Tuple[str, List[str]]:
        """
        处理PDF文档

        Args:
            pdf_path: PDF文件绝对路径
            doc_id: 文档唯一ID
            output_base_dir: 输出基础目录

        Returns:
            (markdown_content, image_filenames)
        """
        logger.info(
            f"🚀 [PDF] 使用 {self.converter_name} 转换器处理PDF: "
            f"doc_id={doc_id}"
        )

        return self.converter_impl.convert_to_markdown(
            pdf_path, doc_id, output_base_dir
        )
```

**关键改动**：
1. 删除所有私有方法（已迁移到Pix2TextConverter）
2. 添加`CONVERTERS`映射表
3. 实现`_load_converter()`动态加载机制
4. 实现`converter_impl`懒加载属性
5. 添加优雅降级逻辑

#### 步骤1.6：创建转换器枚举模型
**文件**: `backend/app/models/document.py`（新建或修改）

```python
"""文档相关数据模型"""
from enum import Enum


class ConverterType(str, Enum):
    """
    PDF转换器类型枚举

    值说明:
    - pix2text: 快速OCR+公式识别（默认）
    - marker: 高精度布局识别
    """
    pix2text = "pix2text"
    marker = "marker"
```

#### 步骤1.7：扩展API接口
**文件**: `backend/app/api/v1/documents.py`（修改）

```python
from app.models.document import ConverterType  # 新增导入

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    converter: ConverterType = ConverterType.pix2text,  # ✅ 新增参数，默认pix2text
    background_tasks: BackgroundTasks = None
) -> DocumentUploadResponse:
    """
    上传文档并保存到本地

    支持格式: PDF, DOCX

    ✅ 新增参数:
    - converter: PDF转换器选择
      - pix2text: 快速OCR+公式识别（默认），速度3-5秒/页
      - marker: 高精度布局识别，速度8-15秒/页，质量更高

    转换器选择建议:
    - 学术论文、公式多的文档 → pix2text
    - 复杂布局、表格密集文档 → marker
    """
    logger.info(
        f"📤 [API] 收到上传请求: "
        f"filename='{file.filename}', "
        f"converter='{converter.value}'"
    )

    # ... 现有的文件验证逻辑 ...

    # ✅ 修改：传递converter参数到后台任务
    if background_tasks:
        logger.info(
            f"⚙️ [API] 添加后台处理任务: "
            f"doc_id={doc_id}, "
            f"converter={converter.value}"
        )
        background_tasks.add_task(
            process_document_background,
            doc_id=doc_id,
            file_path=str(file_path),
            file_type=file_ext[1:],
            output_base_dir=str(settings.processed_dir),
            converter=converter.value  # ✅ 新增参数
        )

    # 根据转换器生成不同的提示消息
    converter_desc = {
        "pix2text": "快速转换",
        "marker": "高质量转换"
    }.get(converter.value, converter.value)

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status="processing",
        message=f"文档正在处理中 (使用{converter.value}转换器，{converter_desc})",
        file_size=file_size
    )
```

#### 步骤1.8：修改文档处理协调器
**文件**: `backend/app/core/document_processor.py`（修改）

```python
async def process_document_background(
    doc_id: str,
    file_path: str,
    file_type: str,
    output_base_dir: str,
    converter: str = "pix2text"  # ✅ 新增参数，默认pix2text
) -> None:
    """
    后台异步处理文档

    Args:
        doc_id: 文档唯一 ID
        file_path: 原始文件路径
        file_type: 文件类型
        output_base_dir: 输出基础目录
        converter: PDF转换器名称 (pix2text/marker) ✅ 新增

    Returns:
        None
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

    # ... 系统资源监控代码保持不变 ...

    try:
        # ✅ 修改：传递converter参数到PDFProcessor
        logger.info(f"📄 [BG] 步骤1: 选择处理器 (file_type={file_type}, converter={converter})")

        if file_type.lower() == "pdf":
            processor = PDFProcessor(converter=converter)  # ✅ 新增参数
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

        # 处理器信息
        logger.debug(
            f"🔧 [BG] 处理器实例: {processor.__class__.__name__}, "
            f"converter={converter}, "
            f"device={processor.device}"
        )

        # ... 其余逻辑保持不变 ...
```

#### 步骤1.9：创建转换器模块初始化
**文件**: `backend/app/core/converters/__init__.py`（新建）

```python
"""PDF转换器模块"""

from .base import PDFConverterBase
from .pix2text_converter import Pix2TextConverter
from .marker_converter import MarkerConverter

__all__ = [
    "PDFConverterBase",
    "Pix2TextConverter",
    "MarkerConverter",
]
```

---

### 阶段2：前端UI实现（2-3小时）

#### 步骤2.1：添加转换器类型定义
**文件**: `frontend/src/types/document.ts`（修改）

```typescript
/**
 * 文档相关类型定义
 */

// ... 现有类型定义保持不变 ...

/**
 * ✅ 新增：PDF转换器类型
 */
export const ConverterType = {
  PIX2TEXT: 'pix2text',
  MARKER: 'marker',
} as const;

export type ConverterType = (typeof ConverterType)[keyof typeof ConverterType];

/**
 * ✅ 新增：转换器选项配置
 */
export const CONVERTER_OPTIONS: Record<
  ConverterType,
  { label: string; description: string; features: string[]; speed: 'fast' | 'slow' }
> = {
  pix2text: {
    label: 'Pix2Text (快速，推荐)',
    description: '处理速度快，适合大多数文档',
    features: ['处理速度快', '公式识别准确', '适合学术论文'],
    speed: 'fast',
  },
  marker: {
    label: 'Marker (高质量)',
    description: '质量更高，适合复杂布局和表格较多的文档',
    features: ['布局识别精准', '表格还原效果好', '适合复杂文档'],
    speed: 'slow',
  },
};
```

#### 步骤2.2：修改上传服务
**文件**: `frontend/src/services/document.ts`（修改）

```typescript
import type { ConverterType } from '../types/document';  // ✅ 新增导入

class DocumentService {
  private readonly basePath = '/documents';

  /**
   * 上传文档
   * ✅ 修改：添加converter参数
   *
   * @param file 文件对象
   * @param converter PDF转换器类型 (默认: pix2text)
   * @returns 上传响应
   */
  async uploadDocument(
    file: File,
    converter: ConverterType = 'pix2text'  // ✅ 新增参数，默认值
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('converter', converter);  // ✅ 添加converter字段

    const response = await apiClient.post<UploadResponse>(
      `${this.basePath}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  // ... 其他方法保持不变 ...
}
```

#### 步骤2.3：更新Document Store
**文件**: `frontend/src/store/documentStore.ts`（修改）

```typescript
import type { ConverterType } from '../types/document';  // ✅ 新增导入

interface DocumentState {
  // ... 现有状态保持不变 ...

  // ✅ 修改：uploadDocument方法签名
  uploadDocument: (file: File, converter?: ConverterType) => Promise<string>;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  // ... 初始状态保持不变 ...

  // ✅ 修改：添加converter参数
  uploadDocument: async (file: File, converter: ConverterType = 'pix2text') => {
    set({ isLoading: true, error: null });
    try {
      const response = await documentService.uploadDocument(file, converter);  // ✅ 传递converter

      const newDoc: Document = {
        doc_id: response.doc_id,
        filename: response.filename,
        file_size: response.file_size,
        status: response.status,
        upload_time: Date.now() / 1000,
      };

      set((state) => ({
        documents: [newDoc, ...state.documents],
        isLoading: false,
      }));

      return response.doc_id;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '上传文档失败',
        isLoading: false,
      });
      throw error;
    }
  },

  // ... 其他方法保持不变 ...
}));
```

#### 步骤2.4：重构FileUpload组件
**文件**: `frontend/src/components/FileUpload.tsx`（修改）

```typescript
/**
 * 文件上传组件
 * ✅ 新增：PDF转换器下拉选择器
 */
import React, { useState, useRef } from 'react';
import { Upload, FileText, X, Info } from 'lucide-react';  // ✅ 新增Info图标
import { useDocumentStore } from '../store';
import { useUIStore } from '../store';
import { CONVERTER_OPTIONS, type ConverterType } from '../types/document';  // ✅ 新增导入

const FileUpload: React.FC = () => {
  const { uploadDocument, isLoading } = useDocumentStore();
  const { showNotification } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedConverter, setSelectedConverter] = useState<ConverterType>('pix2text');  // ✅ 新增状态
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ... 现有的验证和文件处理逻辑保持不变 ...

  /**
   * 上传文件
   * ✅ 修改：传递converter参数
   */
  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      await uploadDocument(selectedFile, selectedConverter);  // ✅ 传递选中的转换器

      const converterLabel = CONVERTER_OPTIONS[selectedConverter].label;
      showNotification(
        `成功上传: ${selectedFile.name} (使用${converterLabel})`,
        'success'
      );

      setSelectedFile(null);
      setSelectedConverter('pix2text');  // ✅ 重置为默认值
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      showNotification(
        error instanceof Error ? error.message : '上传失败',
        'error'
      );
    }
  };

  /**
   * 取消选择
   * ✅ 修改：重置转换器选择
   */
  const handleCancel = () => {
    setSelectedFile(null);
    setSelectedConverter('pix2text');  // ✅ 重置为默认值
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      {/* ✅ 新增：转换器选择下拉菜单 */}
      <div className="mb-4">
        <label
          htmlFor="converter-select"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          选择PDF转换器
        </label>
        <select
          id="converter-select"
          value={selectedConverter}
          onChange={(e) => setSelectedConverter(e.target.value as ConverterType)}
          disabled={isLoading}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-primary-500
                     disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          <option value="pix2text">{CONVERTER_OPTIONS.pix2text.label}</option>
          <option value="marker">{CONVERTER_OPTIONS.marker.label}</option>
        </select>

        {/* 转换器说明文字 */}
        <div className="mt-2 flex items-start space-x-2 text-xs text-gray-600">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p>
            {CONVERTER_OPTIONS[selectedConverter].description}
            {' '}(特性: {CONVERTER_OPTIONS[selectedConverter].features.join('、')})
          </p>
        </div>
      </div>

      {/* 文件上传区域（保持现有逻辑不变） */}
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {/* ... 现有的文件上传UI保持不变 ... */}
      </div>

      {/* 操作按钮（保持现有逻辑不变） */}
      {selectedFile && (
        <div className="mt-4 flex space-x-3">
          <button
            onClick={handleUpload}
            disabled={isLoading}
            className="btn-primary flex-1"
          >
            {isLoading ? '上传中...' : '开始上传'}
          </button>
          <button
            onClick={handleCancel}
            disabled={isLoading}
            className="btn-secondary flex-1"
          >
            取消
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
```

**关键改动**：
1. 导入`CONVERTER_OPTIONS`和`ConverterType`类型
2. 添加`selectedConverter`状态（默认`'pix2text'`）
3. 在文件上传区前添加下拉菜单
4. 动态显示选中转换器的说明文字
5. 上传时传递`selectedConverter`参数
6. 上传成功/取消后重置为默认值

---

### 阶段3：测试和验证（1-2小时）

#### 步骤3.1：后端单元测试
**文件**: `backend/tests/test_converters.py`（新建）

```python
"""
测试PDF转换器功能
"""
import pytest
from pathlib import Path
from app.core.converters import Pix2TextConverter, MarkerConverter
from app.core.pdf_processor import PDFProcessor


class TestPix2TextConverter:
    def test_initialization(self):
        """测试Pix2Text转换器初始化"""
        converter = Pix2TextConverter(device="cpu")
        assert converter.device == "cpu"

    def test_convert_to_markdown(self, sample_pdf_path):
        """测试PDF转换功能"""
        converter = Pix2TextConverter(device="cpu")
        markdown, images = converter.convert_to_markdown(
            pdf_path=str(sample_pdf_path),
            doc_id="test-doc",
            output_base_dir="/tmp/test_output"
        )
        assert isinstance(markdown, str)
        assert isinstance(images, list)
        assert len(markdown) > 0


class TestMarkerConverter:
    def test_initialization(self):
        """测试Marker转换器初始化（如果已安装）"""
        try:
            import marker
            converter = MarkerConverter(device="cpu")
            assert converter.device == "cpu"
        except ImportError:
            pytest.skip("marker未安装")

    def test_convert_to_markdown(self, sample_pdf_path):
        """测试PDF转换功能（如果已安装）"""
        try:
            import marker
        except ImportError:
            pytest.skip("marker未安装")

        converter = MarkerConverter(device="cpu")
        markdown, images = converter.convert_to_markdown(
            pdf_path=str(sample_pdf_path),
            doc_id="test-doc",
            output_base_dir="/tmp/test_output"
        )
        assert isinstance(markdown, str)
        assert isinstance(images, list)


class TestPDFProcessor:
    def test_load_pix2text_converter(self):
        """测试加载Pix2Text转换器"""
        processor = PDFProcessor(converter="pix2text")
        assert processor.converter_name == "pix2text"

    def test_load_marker_converter(self):
        """测试加载Marker转换器（如果已安装）"""
        try:
            import marker
            processor = PDFProcessor(converter="marker")
            assert processor.converter_name == "marker"
        except ImportError:
            pytest.skip("marker未安装")

    def test_invalid_converter(self):
        """测试无效转换器"""
        with pytest.raises(ValueError, match="不支持的转换器"):
            PDFProcessor(converter="invalid")
```

**运行测试**：
```bash
cd backend
pytest tests/test_converters.py -v
```

#### 步骤3.2：API集成测试
**文件**: `backend/tests/test_api_upload.py`（新建）

```python
"""
测试上传API的converter参数
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_upload_with_pix2text(sample_pdf_file):
    """测试使用Pix2Text转换器上传"""
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"converter": "pix2text"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    assert "pix2text" in data["message"]


def test_upload_with_marker(sample_pdf_file):
    """测试使用Marker转换器上传（如果已安装）"""
    try:
        import marker
    except ImportError:
        pytest.skip("marker未安装")

    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"converter": "marker"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    assert "marker" in data["message"]


def test_upload_default_converter(sample_pdf_file):
    """测试默认转换器（pix2text）"""
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
            # 不传递converter参数
        )
    assert response.status_code == 200
```

#### 步骤3.3：端到端测试
**测试流程**：

1. **测试Pix2Text转换**：
   ```bash
   # 前端选择Pix2Text，上传PDF
   # 验证：文档处理成功，Markdown格式正确
   ```

2. **测试Marker转换**（如果已安装）：
   ```bash
   # 前端选择Marker，上传PDF
   # 验证：文档处理成功，Markdown格式正确
   ```

3. **测试默认转换器**：
   ```bash
   # 前端不选择，使用默认值
   # 验证：自动使用Pix2Text
   ```

4. **测试优雅降级**：
   ```bash
   # 卸载marker，选择Marker上传
   # 验证：自动降级到Pix2Text，给出警告
   ```

---

## ✅ 兼容性保证

### 后端兼容性

**1. 默认值兼容**
- `converter`参数默认值为`"pix2text"`（现有实现）
- 未传递参数时自动使用默认值
- 现有客户端无需修改

**2. 响应格式兼容**
- `DocumentUploadResponse`结构完全不变
- `DocumentInfo`结构完全不变
- 仅`message`字段附加转换器信息（字符串拼接，不影响解析）

**3. 错误处理兼容**
- `.error`文件格式保持不变
- 新增字段不影响现有错误解析逻辑
- 错误类型和异常层级保持一致

### 前端兼容性

**1. TypeScript类型安全**
- `converter`参数为可选参数
- 默认值`'pix2text'`保持现有行为
- 现有调用代码无需修改

**2. UI渐进式增强**
- 下拉菜单默认显示，不影响现有布局
- 未选择文件时可以切换转换器
- 已选择文件后仍可切换（取消后重置）

**3. 状态管理兼容**
- `Document`接口不增加`converter`字段
- `uploadDocument`方法签名向后兼容
- Store状态结构不变

### 优雅降级机制

**1. Marker未安装**
```python
try:
    import marker
    return MarkerConverter(device)
except ImportError:
    logger.warning("⚠️ marker未安装，自动降级到pix2text")
    return Pix2TextConverter(device)
```

**2. GPU内存不足**
```python
try:
    converter = MarkerConverter(device="cuda")
except RuntimeError as e:
    if "out of memory" in str(e).lower():
        logger.warning("⚠️ GPU内存不足，降级到CPU")
        converter = MarkerConverter(device="cpu")
```

**3. 转换失败回退**
```python
try:
    markdown, images = marker_converter.convert(...)
except Exception as e:
    logger.error(f"❌ Marker转换失败: {e}，尝试Pix2Text")
    markdown, images = pix2text_converter.convert(...)
```

---

## 📊 性能对比和建议

### 转换器特性对比

| 特性 | Pix2Text | Marker | 推荐场景 |
|------|----------|--------|----------|
| **处理速度** | 快（3-5秒/页） | 慢（8-15秒/页） | Pix2Text：实时预览<br>Marker：后台批量 |
| **GPU内存** | 低（~500MB） | 高（~5GB） | Pix2Text：集成显卡<br>Marker：独立显卡 |
| **布局识别** | 标准 | 高精度 | Pix2Text：简单文档<br>Marker：复杂排版 |
| **表格还原** | 良好 | 优秀 | Pix2Text：简单表格<br>Marker：复杂表格 |
| **公式识别** | 优秀 | 良好 | Pix2Text：数理论文<br>Marker：一般文档 |
| **图像提取** | PyMuPDF | 内置 | 质量相当 |
| **Markdown质量** | 标准 | 结构化 | Pix2Text：文本为主<br>Marker：版式复杂 |

### 选择建议

**使用Pix2Text的场景**：
- ✅ 学术论文（公式密集）
- ✅ 需要快速预览
- ✅ GPU内存有限（<8GB）
- ✅ 简单布局文档
- ✅ 集成显卡设备

**使用Marker的场景**：
- ✅ 复杂布局（多栏、嵌套表格）
- ✅ 表格密集文档
- ✅ 高质量还原要求
- ✅ 后台批量处理
- ✅ 独立显卡（8GB+ VRAM）

---

## 🧪 测试清单

### 后端测试

- [ ] `Pix2TextConverter`单元测试
- [ ] `MarkerConverter`单元测试（如果已安装）
- [ ] `PDFProcessor`门面类测试
- [ ] API上传接口测试（两种转换器）
- [ ] 优雅降级测试（卸载marker）
- [ ] GPU/CPU切换测试
- [ ] 图像路径转换测试

### 前端测试

- [ ] 下拉菜单渲染测试
- [ ] 转换器选择状态测试
- [ ] API调用参数测试
- [ ] 上传成功重置测试
- [ ] TypeScript类型检查

### 集成测试

- [ ] 端到端上传流程（Pix2Text）
- [ ] 端到端上传流程（Marker）
- [ ] 文档轮询和状态更新
- [ ] Markdown渲染正确性
- [ ] 图像显示正确性

---

## 📚 相关文档

- **marker GitHub**: https://github.com/datalab-to/marker
- **marker PyPI**: https://pypi.org/project/marker-pdf/
- **Datalab文档**: https://documentation.datalab.to/docs/recipes/marker/conversion-api-overview
- **项目CLAUDE.md**: `backend/CLAUDE.md`, `frontend/src/`
- **Phase 2计划**: `devplan_phase2_frontend.md`

---

## ⏱️ 预估时间

| 阶段 | 任务 | 时间 |
|------|------|------|
| 阶段1 | 后端核心实现 | 3-4小时 |
| 阶段2 | 前端UI实现 | 2-3小时 |
| 阶段3 | 测试和验证 | 1-2小时 |
| | **总计** | **6-9小时** |

---

## 🎯 实施优先级

**P0（必须）**：
1. 后端转换器基类和Pix2Text迁移
2. Marker转换器实现
3. PDFProcessor门面类重构
4. API接口扩展（converter参数）
5. 前端下拉菜单和状态管理

**P1（重要）**：
1. 优雅降级机制
2. 单元测试
3. API集成测试
4. 错误日志优化

**P2（可选）**：
1. 端到端测试
2. 性能监控
3. 文档更新
4. 用户指南

---

## 🔄 回滚计划

如果实施过程中遇到问题，回滚步骤：

1. **后端回滚**：
   ```bash
   cd backend
   git revert <commit-hash>
   pip uninstall marker-pdf
   ```

2. **前端回滚**：
   ```bash
   cd frontend
   git revert <commit-hash>
   ```

3. **数据库回滚**：无（不涉及数据库修改）

---

## 📝 注意事项

### 开发注意事项

1. **GPU内存管理**：
   - 不要同时初始化两种转换器
   - 使用懒加载避免启动时加载
   - 考虑实现转换器缓存和释放机制

2. **图像路径处理**：
   - Marker的图像引用格式可能不一致
   - 需要测试多种PDF文档验证路径转换逻辑
   - 考虑使用正则表达式兼容多种格式

3. **错误处理**：
   - 所有转换器错误都要捕获并转换为`ProcessingError`
   - 详细的日志记录便于排查问题
   - 优雅降级避免用户体验中断

### 测试注意事项

1. **marker安装**：
   - 确保测试环境已安装marker-pdf
   - Python版本需要3.10+
   - PyTorch版本需要兼容

2. **GPU测试**：
   - 测试CUDA和CPU两种模式
   - 测试GPU内存不足情况
   - 测试GPU初始化失败降级

3. **性能测试**：
   - 对比两种转换器的处理时间
   - 监控GPU和内存使用情况
   - 测试大文件（100+页）的稳定性

---

**Sources**:
- [Marker GitHub Repository](https://github.com/datalab-to/marker)
- [marker-pdf PyPI Package](https://pypi.org/project/marker-pdf/)
- [Marker GPU Memory Discussion](https://github.com/datalab-to/marker/issues/160)
- [Marker CUDA Out-of-Memory Issue](https://github.com/datalab-to/marker/issues/710)
- [Medium: Marker PDF to Markdown Guide](https://medium.com/@pankaj_pandey/marker-convert-documents-to-markdown-json-html-quickly-and-accurately-a5afc9aa564e)
- [Deep Dive into Marker](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/)
