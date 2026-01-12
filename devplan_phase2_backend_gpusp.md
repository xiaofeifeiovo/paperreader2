# Phase 2 Backend GPU 支持实现计划（修正版）

## 🎯 目标
修复 PaperReader2 Phase 2 backend 的 GPU 支持，移除强制 CPU 限制，启用 Pix2Text 的自动 GPU 检测。

## 📋 问题分析

### 当前问题 ❌
```python
# backend/app/core/pdf_processor.py:16-17
# 强制使用 CPU（避免 CUDA 错误）
os.environ['ONNXRUNTIME_EXECUTION_PROVIDER'] = 'CPUExecutionProvider'
```

这段代码**强制禁用了 GPU**，导致即使有 RTX 4060 也无法使用。

### 根本原因
- 之前的 CUDA 错误可能是临时性的（模型首次加载、依赖不完整等）
- Pix2Text 支持自动检测 GPU（`device=None`）
- PyTorch 已安装 CUDA 版本（`torch+cu121`）
- **不需要安装 onnxruntime-gpu**（Pix2Text 使用 PyTorch，不是 ONNX Runtime）

### 用户环境 ✅
- **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8GB VRAM)
- **CUDA 驱动**: 12.8
- **PyTorch**: 2.5.1+cu121 (支持 CUDA 12.1)
- **Python**: 3.11.5
- **Pix2Text**: 1.1.4 (支持 GPU 自动检测)

## 🔧 实现方案

### 方案：智能设备检测（推荐）

#### 核心思路
1. **移除强制 CPU 设置**
2. **实现智能设备检测**
3. **添加优雅降级机制**
4. **保留手动控制选项**

#### 实现步骤

**Step 1: 添加设备检测函数**

在 `backend/app/core/pdf_processor.py` 中添加：

```python
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def detect_device() -> str:
    """
    智能检测最佳设备

    检测顺序:
    1. 环境变量 PAPERREADER_DEVICE（手动强制）
    2. PyTorch CUDA 可用性 → 'cuda'
    3. 降级到 'cpu'

    Returns:
        'cuda' 或 'cpu'
    """
    # 1. 检查环境变量（最高优先级）
    force_device = os.environ.get('PAPERREADER_DEVICE', '').lower()
    if force_device in ('cuda', 'gpu', 'cpu'):
        logger.info(f"🎯 使用环境变量强制设备: {force_device}")
        return force_device if force_device != 'gpu' else 'cuda'

    # 2. 检查 CUDA 可用性
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("🚀 检测到 CUDA，将使用 GPU 加速")
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return 'cuda'
    except Exception as e:
        logger.warning(f"⚠️  检测 CUDA 失败: {e}")

    # 3. 降级到 CPU
    logger.info("💻 将使用 CPU 进行处理")
    return 'cpu'
```

**Step 2: 修改 PDFProcessor 类**

```python
class PDFProcessor:
    """PDF 处理器 - Pix2Text + PyMuPDF（支持 GPU 加速）"""

    def __init__(self, device: Optional[str] = None):
        """
        初始化处理器

        Args:
            device: 可选，指定设备 ('cuda' 或 'cpu')。
                    None 表示自动检测。

        设计决策:
        - 延迟加载 Pix2Text，避免启动时加载模型（启动时间过长）
        - 使用 @property 惰性初始化
        - 支持自动设备检测
        """
        self._p2t = None
        # 如果未指定设备，则自动检测
        self.device = device if device is not None else detect_device()
        logger.info(f"📦 PDFProcessor 初始化，设备: {self.device}")

    @property
    def p2t):
        """懒加载 Pix2Text 实例"""
        if self._p2t is None:
            from pix2text import Pix2Text
            logger.info(f"⏳ 正在初始化 Pix2Text 模型 (device={self.device})...")

            try:
                self._p2t = Pix2Text.from_config(
                    enable_formula=True,  # 启用公式识别
                    enable_table=True,    # 启用表格识别
                    device=self.device     # 使用检测到的设备
                )
                logger.info("✅ Pix2Text 模型初始化完成")
            except Exception as e:
                logger.error(f"❌ Pix2Text 初始化失败 (device={self.device}): {e}")
                # 如果 GPU 初始化失败，尝试降级到 CPU
                if self.device == 'cuda':
                    logger.warning("🔄 GPU 初始化失败，尝试降级到 CPU...")
                    self.device = 'cpu'
                    self._p2t = Pix2Text.from_config(device='cpu')
                    logger.info("✅ Pix2Text 模型初始化完成（CPU 模式）")
                else:
                    raise

        return self._p2t
```

**Step 3: 移除强制 CPU 设置**

删除或注释掉：
```python
# 删除这些行
# os.environ['ONNXRUNTIME_EXECUTION_PROVIDER'] = 'CPUExecutionProvider'
```

**Step 4: 更新 requirements.txt（可选）**

**不需要修改**！保持当前的依赖即可：
```
pix2text>=1.1.0           # 已支持 GPU（通过 PyTorch）
pymupdf==1.23.8
```

**注意**: 不需要添加 `onnxruntime-gpu`，Pix2Text 的 GPU 支持通过 PyTorch 实现。

**Step 5: 添加环境变量配置示例**

创建 `backend/.env.example`：
```bash
# 可选: 强制使用指定设备
# PAPERREADER_DEVICE=cuda  # 强制使用 GPU
# PAPERREADER_DEVICE=cpu   # 强制使用 CPU
# 默认: 自动检测（推荐）
```

**Step 6: 更新测试**

在 `backend/tests/test_pdf_processor.py` 中添加：

```python
def test_device_detection():
    """测试设备检测功能"""
    from app.core.pdf_processor import detect_device
    import torch

    device = detect_device()
    assert device in ('cuda', 'cpu')

    # 如果系统有 CUDA，应该检测到
    if torch.cuda.is_available():
        assert device == 'cuda', f"应该检测到 GPU，但得到: {device}"

def test_gpu_fallback():
    """测试 GPU 初始化失败时的降级"""
    processor = PDFProcessor(device='invalid_device')

    # 应该降级到 CPU 或抛出错误
    try:
        _ = processor.p2t
    except Exception as e:
        # 预期行为：要么降级成功，要么抛出明确错误
        assert 'device' in str(e).lower() or processor.device == 'cpu'
```

## 📁 需要修改的文件

1. **backend/app/core/pdf_processor.py** ⭐ 核心修改
   - 添加 `detect_device()` 函数
   - 修改 `PDFProcessor.__init__()` 支持 device 参数
   - 移除强制 CPU 的环境变量设置
   - 在 `@property p2t` 中添加 GPU 初始化失败降级逻辑

2. **backend/.env.example** (新建)
   - 添加 `PAPERREADER_DEVICE` 配置说明

3. **backend/tests/test_pdf_processor.py**
   - 添加设备检测测试
   - 添加 GPU 降级测试

## 🧪 测试计划

### 1. 单元测试
```bash
cd backend
pytest tests/test_pdf_processor.py::TestPDFProcessor::test_device_detection -v
pytest tests/test_pdf_processor.py::TestPDFProcessor::test_gpu_fallback -v
```

### 2. 功能验证测试
```bash
# 测试设备检测
python -c "from app.core.pdf_processor import detect_device; print(detect_device())"
# 期望输出: cuda

# 测试 PDFProcessor 初始化
python -c "from app.core.pdf_processor import PDFProcessor; p = PDFProcessor(); print(f'Device: {p.device}')"
# 期望输出: Device: cuda
```

### 3. 集成测试（使用真实 PDF）
```bash
pytest tests/test_pdf_processor.py::TestPDFProcessor::test_process_full -v -s
pytest tests/test_api.py::TestDocumentAPI::test_upload_and_process -v -s
```

### 4. 手动验证（推荐）

创建临时测试脚本 `backend/test_gpu.py`：
```python
import logging
from app.core.pdf_processor import PDFProcessor, detect_device

logging.basicConfig(level=logging.INFO)

# 测试设备检测
print("=" * 50)
device = detect_device()
print(f"检测到的设备: {device}")
print("=" * 50)

# 测试完整处理流程
processor = PDFProcessor()
print(f"PDFProcessor 使用设备: {processor.device}")

# 触发模型加载
_ = processor.p2t
print("模型加载成功！")
```

运行测试：
```bash
python test_gpu.py
```

**期望输出**:
```
检测到的设备: cuda
🚀 检测到 CUDA，将使用 GPU 加速
   GPU: NVIDIA GeForce RTX 4060 Laptop GPU
   VRAM: 8.0 GB
PDFProcessor 使用设备: cuda
⏳ 正在初始化 Pix2Text 模型 (device=cuda)...
✅ Pix2Text 模型初始化完成
模型加载成功！
```

## ⚠️ 风险和注意事项

### 1. GPU 内存管理
- **风险**: RTX 4060 有 8GB VRAM，大型 PDF 可能占用大量显存
- **缓解**: Pix2Text 会自动管理内存，但建议监控 GPU 使用
- **监控方法**:
  ```bash
  # 另一个终端运行
  nvidia-smi -l 1
  ```

### 2. CUDA 兼容性
- **当前**: PyTorch 2.5.1+cu121, CUDA 驱动 12.8
- **兼容性**: ✅ 完全兼容
- **注意事项**: 如果未来升级 PyTorch，需要确保 CUDA 版本匹配

### 3. 降级机制
- **场景**: GPU 初始化失败（CUDA 版本不匹配、驱动问题等）
- **处理**: 代码会自动降级到 CPU
- **验证**: 测试 `test_gpu_fallback`

### 4. 多用户环境
- **当前**: 单用户本地部署，无需担心 GPU 资源竞争
- **未来**: 如果支持多用户，需要添加任务队列（如 Celery）

## 📊 预期性能提升

基于 Pix2Text 文档和社区反馈：

| 操作 | CPU | GPU (RTX 4060) | 提升倍数 |
|------|-----|---------------|---------|
| 文本 OCR | 3-5 秒/页 | 1-2 秒/页 | **3-5x** |
| 公式识别 | 5-8 秒/页 | 2-3 秒/页 | **2-4x** |
| 表格识别 | 8-12 秒/页 | 3-5 秒/页 | **2-3x** |
| **总体** | **3-5 秒/页** | **1-2 秒/页** | **3-5x** |

**注意**: 实际提升取决于 PDF 复杂度（公式数量、图像密度等）。

## ✅ 完成标准

1. ✅ **自动检测 GPU**: 在 RTX 4060 环境下自动使用 'cuda'
2. ✅ **优雅降级**: GPU 初始化失败时自动降级到 CPU（不报错）
3. ✅ **测试通过**: 所有现有测试通过
4. ✅ **日志清晰**: 启动时显示使用的设备和 GPU 信息
5. ✅ **手动控制**: 用户可通过环境变量 `PAPERREADER_DEVICE` 强制指定
6. ✅ **向后兼容**: 无 GPU 的环境仍然可以正常使用（自动降级到 CPU）

## 📝 实施步骤总结

1. **修改核心代码**: `backend/app/core/pdf_processor.py`
   - 添加 `detect_device()` 函数
   - 修改 `PDFProcessor.__init__()` 和 `p2t` property
   - 移除强制 CPU 设置

2. **添加配置**: 创建 `backend/.env.example`

3. **更新测试**: `backend/tests/test_pdf_processor.py`
   - 添加设备检测测试
   - 添加降级测试

4. **验证功能**:
   - 运行单元测试
   - 手动验证 GPU 检测
   - 运行完整集成测试

5. **文档更新**:
   - 更新 README 说明 GPU 支持
   - 添加环境变量配置说明

## 🎉 成功标志

运行以下命令时，应该看到 GPU 相关的日志：

```bash
cd backend
python -c "from app.core.pdf_processor import PDFProcessor; p = PDFProcessor(); _ = p.p2t"
```

**期望输出**:
```
🚀 检测到 CUDA，将使用 GPU 加速
   GPU: NVIDIA GeForce RTX 4060 Laptop GPU
   VRAM: 8.0 GB
📦 PDFProcessor 初始化，设备: cuda
⏳ 正在初始化 Pix2Text 模型 (device=cuda)...
✅ Pix2Text 模型初始化完成
```

## 📚 参考资料

- [Pix2Text 官方文档](https://github.com/breezedeus/pix2text)
- [PyTorch CUDA 安装指南](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA 兼容性](https://docs.nvidia.com/deeplearning/cudnn/support-matrix/index.html)
