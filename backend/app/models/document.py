"""文档相关数据模型"""
from enum import Enum


class ConverterType(str, Enum):
    """
    PDF转换器类型枚举

    值说明:
    - pix2text: 快速OCR+公式识别(默认)
    - marker: 高精度布局识别
    """
    pix2text = "pix2text"
    marker = "marker"
