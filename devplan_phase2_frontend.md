# Phase 2 前端实施计划 - Markdown渲染与文档查看

> **创建时间**: 2026-01-12
> **预计工期**: 5天
> **优先级**: 🔴 高

## 📋 任务概述

实现Phase 2的前端核心功能：Markdown渲染、数学公式支持、图像懒加载、文档查看页面和状态轮询。

## 🔍 关键发现与问题

### ⚠️ 后端与前端类型不匹配问题

经过深入分析后端代码，发现了**严重的前后端类型不一致**问题：

#### 问题1: 文档状态枚举不匹配

| 场景 | 后端返回值 | 前端类型定义 | 状态 |
|------|-----------|-------------|------|
| 处理完成 | `"ready"` | `COMPLETED: 'completed'` | ❌ 不匹配 |
| 处理失败 | `"failed"` | `FAILED: 'failed'` | ✅ 匹配 |
| 处理中 | `"processing"` | `PROCESSING: 'processing'` | ✅ 匹配 |
| 上传中 | - | `UPLOADING: 'uploading'` | ⚠️ 前端独有 |

**影响**：文档列表永远显示"处理中"，即使后端返回 `ready`

#### 问题2: DocumentContent 字段不匹配

**后端实际返回** (`GET /api/v1/documents/{doc_id}`):
```json
{
  "doc_id": "uuid",
  "content": "# 标题\nMarkdown内容...",
  "images": ["img_001", "img_002"],
  "status": "ready"
}
```

**前端类型定义** (`types/document.ts`):
```typescript
export interface DocumentContent {
  doc_id: string;
  filename: string;    // ❌ 后端没有
  markdown: string;    // ❌ 应该是 content
  images: string[];
  created_at: string;  // ❌ 后端没有
}
```

**影响**：获取文档内容时会访问 `undefined.markdown` 导致错误

#### 问题3: 文档列表字段不匹配

**后端返回**:
```json
{
  "documents": [
    {
      "doc_id": "uuid",
      "filename": "file.pdf",
      "status": "ready",
      "upload_time": 1625097600.0,  // Unix时间戳（浮点数）
      "file_size": 1234567
    }
  ]
}
```

**前端期望** (`types/document.ts`):
```typescript
export interface Document {
  doc_id: string;
  filename: string;
  file_size: number;
  file_type: string;    // ❌ 后端没有
  status: DocumentStatus;
  created_at: string;   // ❌ 后端是 upload_time（浮点数）
  updated_at: string;   // ❌ 后端没有
}
```

### ✅ 修复优先级

这些问题**必须在实现任何新功能之前修复**，否则会导致：
- 状态永远显示错误
- 无法正确显示文档内容
- 类型检查失败

---

## 📦 依赖安装

### 新增依赖包

```bash
cd frontend
npm install remark-math rehype-katex remark-gfm react-router-dom clsx
```

**包用途说明**：
| 包名 | 版本 | 用途 |
|------|------|------|
| `remark-math` | ^6.0.0 | 解析 LaTeX 公式语法 (`$...$` 和 `$$...$$`) |
| `rehype-katex` | ^7.0.0 | 渲染数学公式为 HTML |
| `remark-gfm` | ^4.0.0 | GitHub Flavored Markdown（表格、删除线等） |
| `react-router-dom` | ^6.22.0 | 客户端路由管理 |
| `clsx` | ^2.1.0 | 条件类名工具（替代 `classnames`） |

**当前已有的依赖**：
- ✅ `react-markdown`: ^10.1.0
- ✅ `katex`: ^0.16.27
- ✅ `axios`: ^1.13.2
- ✅ `zustand`: ^5.0.10

---

## 🗂️ 文件变更清单

### 🔴 高优先级：修复类型不匹配（必须先完成）

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `frontend/src/types/document.ts` | **完全重构**，匹配后端API | 1小时 |
| `frontend/src/services/document.ts` | 调整类型引用 | 30分钟 |
| `frontend/src/store/documentStore.ts` | 修复字段映射和类型转换 | 1小时 |

### 🟡 中优先级：核心功能实现

| 文件 | 操作 | 用途 |
|------|------|------|
| `frontend/src/components/MarkdownRenderer.tsx` | **新建** | Markdown + KaTeX渲染 |
| `frontend/src/components/LazyImage.tsx` | **新建** | 图像懒加载 |
| `frontend/src/components/LoadingSpinner.tsx` | **新建** | 加载动画 |
| `frontend/src/components/DocumentViewer.tsx` | **新建** | 文档查看器主组件 |
| `frontend/src/pages/HomePage.tsx` | **新建** | 首页（重构App.tsx） |
| `frontend/src/pages/DocumentViewPage.tsx` | **新建** | 文档查看页面 |
| `frontend/src/hooks/useDocumentPolling.ts` | **新建** | 状态轮询Hook |
| `frontend/src/router/index.tsx` | **新建** | 路由配置 |

### 🟢 低优先级：集成与优化

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `frontend/src/App.tsx` | 集成路由系统 | 30分钟 |
| `frontend/src/index.css` | 添加KaTeX和Markdown样式 | 30分钟 |
| `frontend/src/components/index.ts` | 导出新组件 | 15分钟 |

---

## 🔧 详细实施步骤

### 步骤0: 修复类型不匹配（必须优先完成）

#### 0.1 重构 `types/document.ts`

**完全替换现有内容**：

```typescript
/**
 * 文档相关类型定义
 * ⚠️ 必须与后端API返回格式完全匹配
 */

/**
 * 文档状态枚举
 * 对应后端: app/api/v1/documents.py
 */
export const DocumentStatus = {
  UPLOADING: 'uploading',    // 前端本地状态（上传中）
  PROCESSING: 'processing',  // 后端返回（处理中）
  READY: 'ready',           // 后端返回（处理完成）✅ 修复
  ERROR: 'error',           // 后端返回（处理失败）
} as const;

export type DocumentStatus = (typeof DocumentStatus)[keyof typeof DocumentStatus];

/**
 * 文档信息（来自列表API）
 * 对应后端: GET /api/v1/documents/list
 */
export interface Document {
  doc_id: string;
  filename: string;
  status: DocumentStatus;
  upload_time: number;      // ✅ 修复: Unix时间戳（浮点数）
  file_size: number;
}

/**
 * 文档上传响应
 * 对应后端: POST /api/v1/documents/upload
 */
export interface UploadResponse {
  doc_id: string;
  filename: string;
  status: DocumentStatus;
  message: string;
  file_size: number;
}

/**
 * 文档内容（来自详情API）
 * 对应后端: GET /api/v1/documents/{doc_id}
 */
export interface DocumentContent {
  doc_id: string;
  content: string;         // ✅ 修复: 后端字段名是 content
  images: string[];        // 图像文件名列表，如 ["img_001", "img_002"]
  status: DocumentStatus;
}

/**
 * 文档列表响应
 * 对应后端: GET /api/v1/documents/list
 */
export interface DocumentListResponse {
  documents: Document[];
}

/**
 * API 错误响应
 */
export interface ApiError {
  detail: string;
  status_code: number;
}

/**
 * 健康检查响应
 */
export interface HealthResponse {
  status: string;
  timestamp: string;
}
```

**关键变更**：
1. ✅ `COMPLETED` → `READY`（匹配后端返回值）
2. ✅ `FAILED` → `ERROR`（更语义化）
3. ✅ `Document.markdown` → `DocumentContent.content`
4. ✅ `Document.created_at` → `Document.upload_time`（浮点数）
5. ✅ 移除不存在的字段（`file_type`, `updated_at`, `filename` in DocumentContent）

#### 0.2 修复 `store/documentStore.ts`

**上传文档方法** - 修复类型转换：

```typescript
uploadDocument: async (file: File) => {
  set({ isLoading: true, error: null });
  try {
    const response = await documentService.uploadDocument(file);

    // 创建临时文档对象（匹配后端格式）
    const newDoc: Document = {
      doc_id: response.doc_id,
      filename: response.filename,
      file_size: response.file_size,
      status: response.status,  // ✅ 不再需要类型转换
      upload_time: Date.now() / 1000,  // ✅ Unix时间戳（浮点数）
    };

    set((state) => ({
      documents: [newDoc, ...state.documents],
      isLoading: false,
    }));

    return response.doc_id;
  } catch (error) {
    // ... 错误处理
  }
},
```

**获取文档内容方法** - 新增：

```typescript
// 在 DocumentState 接口中添加
interface DocumentState {
  // ... 现有字段

  // 新增字段
  currentDocumentContent: DocumentContent | null;

  // 新增方法
  fetchDocumentContent: (docId: string) => Promise<DocumentContent>;
}

// 实现
fetchDocumentContent: async (docId: string) => {
  set({ isLoading: true, error: null });
  try {
    const content = await documentService.getDocument(docId);
    set({ currentDocumentContent: content, isLoading: false });
    return content;
  } catch (error) {
    set({
      error: error instanceof Error ? error.message : '获取文档内容失败',
      isLoading: false,
    });
    throw error;
  }
},
```

---

### 步骤1: 实现轮询Hook

**文件**: `frontend/src/hooks/useDocumentPolling.ts`

```typescript
import { useEffect, useState, useRef } from 'react';
import type { DocumentStatus } from '../types';
import { documentService } from '../services';

interface UseDocumentPollingOptions {
  docId: string;
  initialStatus?: DocumentStatus;
  interval?: number;           // 轮询间隔（毫秒）
  maxAttempts?: number;        // 最大轮询次数
  onStatusChange?: (status: DocumentStatus) => void;
  onComplete?: () => void;     // 处理完成回调
  onError?: (error: string) => void; // 处理失败回调
}

interface UseDocumentPollingReturn {
  status: DocumentStatus;
  isPolling: boolean;
  pollingCount: number;
  stopPolling: () => void;
}

/**
 * 文档状态轮询Hook
 *
 * 特性：
 * - 指数退避策略（3s → 5s → 10s）
 * - 自动停止条件（ready/error）
 * - 组件卸载时自动清理
 */
export const useDocumentPolling = ({
  docId,
  initialStatus = 'processing' as DocumentStatus,
  interval = 3000,
  maxAttempts = 100,  // 约5分钟
  onStatusChange,
  onComplete,
  onError,
}: UseDocumentPollingOptions): UseDocumentPollingReturn => {
  const [status, setStatus] = useState<DocumentStatus>(initialStatus);
  const [pollingCount, setPollingCount] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout>();

  // 计算动态轮询间隔（指数退避）
  const calculateInterval = (count: number): number => {
    if (count < 10) return 3000;      // 前10次：每3秒
    if (count < 30) return 5000;      // 10-30次：每5秒
    return 10000;                     // 30次后：每10秒
  };

  // 停止轮询
  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = undefined;
    }
  };

  // 轮询逻辑
  useEffect(() => {
    // 如果初始状态已经是最终状态，不启动轮询
    if (initialStatus === 'ready' || initialStatus === 'error') {
      return;
    }

    const poll = async () => {
      try {
        const doc = await documentService.getDocument(docId);
        const newStatus = doc.status;

        setStatus(newStatus);
        setPollingCount((prev) => {
          const newCount = prev + 1;
          onStatusChange?.(newStatus);

          // 检查停止条件
          if (newStatus === 'ready') {
            stopPolling();
            onComplete?.();
          } else if (newStatus === 'error') {
            stopPolling();
            onError?.('文档处理失败');
          } else if (newCount >= maxAttempts) {
            stopPolling();
            onError?.('文档处理超时');
          }

          return newCount;
        });

        // 动态调整间隔（指数退避）
        stopPolling();
        const nextInterval = calculateInterval(pollingCount);
        intervalRef.current = setInterval(poll, nextInterval);
      } catch (error) {
        stopPolling();
        onError?.(error instanceof Error ? error.message : '获取文档状态失败');
      }
    };

    // 启动轮询
    intervalRef.current = setInterval(poll, interval);

    // 清理函数
    return () => stopPolling();
  }, [docId, initialStatus]);

  return {
    status,
    isPolling: !!intervalRef.current,
    pollingCount,
    stopPolling,
  };
};
```

---

### 步骤2: 实现Markdown渲染器

**文件**: `frontend/src/components/MarkdownRenderer.tsx`

```typescript
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import { LazyImage } from './LazyImage';
import { documentService } from '../services';

interface MarkdownRendererProps {
  content: string;       // Markdown文本
  docId?: string;        // 文档ID（用于解析图像路径）
  className?: string;
}

/**
 * Markdown渲染组件
 *
 * 功能：
 * - 渲染Markdown为HTML
 * - 支持LaTeX数学公式（行内 $...$ 和块级 $$...$$）
 * - 支持GitHub Flavored Markdown（表格、删除线等）
 * - 图像懒加载
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  docId,
  className = '',
}) => {
  return (
    <ReactMarkdown
      className={`prose prose-lg max-w-none ${className}`}
      remarkPlugins={[remarkMath, remarkGfm]}
      rehypePlugins={[rehypeKatex]}
      components={{
        // 自定义图像组件（实现懒加载）
        img: ({ node, src, alt, ...props }) => {
          if (!src) return null;

          // 处理相对路径转换为完整URL
          const getImageUrl = (src: string): string => {
            // 已经是完整URL或绝对路径
            if (src.startsWith('http') || src.startsWith('/')) {
              return src;
            }

            // 相对路径：使用documentService转换
            if (docId) {
              return documentService.getImageUrl(docId, src);
            }

            return src;
          };

          return (
            <LazyImage
              src={getImageUrl(src)}
              alt={alt || ''}
              className="rounded-lg shadow-md my-4"
            />
          );
        },

        // 自定义代码块样式
        code: ({ node, inline, className, children, ...props }) => {
          if (inline) {
            return (
              <code
                className="px-1.5 py-0.5 bg-gray-100 text-red-600 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          }

          return (
            <code
              className={`block bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono ${className || ''}`}
              {...props}
            >
              {children}
            </code>
          );
        },

        // 自定义预格式化块
        pre: ({ children }) => {
          return <div className="my-4">{children}</div>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
};
```

---

### 步骤3: 实现图像懒加载组件

**文件**: `frontend/src/components/LazyImage.tsx`

```typescript
import React, { useState, useRef, useEffect } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
}

/**
 * 图像懒加载组件
 *
 * 功能：
 * - 使用Intersection Observer检测视口
 * - 仅当图像进入视口时才开始加载
 * - 显示骨架屏占位符
 * - 加载失败时显示错误占位符
 */
export const LazyImage: React.FC<LazyImageProps> = ({
  src,
  alt,
  className = '',
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // 创建Intersection Observer
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect(); // 只触发一次
        }
      },
      {
        rootMargin: '200px', // 提前200px开始加载
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  const handleLoad = () => {
    setIsLoaded(true);
    setIsError(false);
  };

  const handleError = () => {
    setIsError(true);
    setIsLoaded(false);
  };

  return (
    <div ref={imgRef} className={`relative ${className}`}>
      {/* 骨架屏占位符 */}
      {!isLoaded && !isError && (
        <div className="animate-pulse bg-gray-200 rounded-lg min-h-[200px] flex items-center justify-center">
          <svg
            className="w-12 h-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </div>
      )}

      {/* 错误占位符 */}
      {isError && (
        <div className="bg-red-50 rounded-lg min-h-[200px] flex flex-col items-center justify-center text-red-600">
          <svg
            className="w-12 h-12 mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-sm">图像加载失败</p>
          <p className="text-xs text-red-500 mt-1">{alt}</p>
        </div>
      )}

      {/* 实际图像 */}
      {isInView && !isError && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onLoad={handleLoad}
          onError={handleError}
          className={`transition-opacity duration-300 ${
            isLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          style={{ display: isLoaded ? 'block' : 'none' }}
        />
      )}
    </div>
  );
};
```

---

### 步骤4: 实现文档查看器组件

**文件**: `frontend/src/components/DocumentViewer.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { useDocumentStore } from '../store';
import { MarkdownRenderer } from './MarkdownRenderer';
import { LoadingSpinner } from './LoadingSpinner';

interface DocumentViewerProps {
  docId: string;
  filename?: string;
  onBack?: () => void;
}

/**
 * 文档查看器主组件
 *
 * 功能：
 * - 加载并显示文档内容
 * - 滚动进度显示
 * - 返回按钮
 */
export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  docId,
  filename,
  onBack,
}) => {
  const { currentDocumentContent, fetchDocumentContent } = useDocumentStore();
  const [scrollProgress, setScrollProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载文档内容
  useEffect(() => {
    const loadContent = async () => {
      try {
        setIsLoading(true);
        setError(null);
        await fetchDocumentContent(docId);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载文档失败');
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [docId, fetchDocumentContent]);

  // 监听滚动进度
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = (scrollTop / docHeight) * 100;
      setScrollProgress(Math.min(100, Math.max(0, progress)));
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-red-600">
        <svg
          className="w-16 h-16 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-lg font-semibold">加载失败</p>
        <p className="text-sm text-gray-600 mt-2">{error}</p>
      </div>
    );
  }

  // 无内容
  if (!currentDocumentContent) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-gray-500">
        文档内容不存在
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* 顶部工具栏 */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-4">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="返回"
            >
              <svg
                className="w-5 h-5 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
          )}
          <h1 className="text-lg font-semibold text-gray-800 truncate">
            {filename || currentDocumentContent.doc_id}
          </h1>
        </div>

        {/* 滚动进度 */}
        <div className="flex items-center space-x-2">
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-150"
              style={{ width: `${scrollProgress}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">{Math.round(scrollProgress)}%</span>
        </div>
      </div>

      {/* 文档内容区域 */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <MarkdownRenderer
            content={currentDocumentContent.content}
            docId={currentDocumentContent.doc_id}
          />
        </div>
      </div>
    </div>
  );
};
```

---

### 步骤5: 实现加载动画组件

**文件**: `frontend/src/components/LoadingSpinner.tsx`

```typescript
import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

/**
 * 加载动画组件
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  className = '',
}) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12',
  };

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <svg
        className={`animate-spin ${sizeClasses[size]} text-blue-600`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
};
```

---

### 步骤6: 配置路由系统

**文件**: `frontend/src/router/index.tsx`

```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../layout';
import { HomePage } from '../pages/HomePage';
import { DocumentViewPage } from '../pages/DocumentViewPage';

/**
 * 路由配置
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'document/:docId',
        element: <DocumentViewPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
```

---

### 步骤7: 创建页面组件

**文件**: `frontend/src/pages/HomePage.tsx`

```typescript
import React from 'react';
import { FileUpload, DocumentList } from '../components';

/**
 * 首页组件
 */
export const HomePage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* 欢迎区域 */}
      <div className="text-center py-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          欢迎使用 PaperReader2
        </h1>
        <p className="text-lg text-gray-600">
          AI 增强型论文阅读器 - 支持智能问答和 Markdown 渲染
        </p>
      </div>

      {/* 文件上传区域 */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">上传文档</h2>
        <FileUpload />
      </div>

      {/* 文档列表 */}
      <DocumentList />
    </div>
  );
};
```

**文件**: `frontend/src/pages/DocumentViewPage.tsx`

```typescript
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DocumentViewer } from '../components';
import { useDocumentStore } from '../store';

/**
 * 文档查看页面
 */
export const DocumentViewPage: React.FC = () => {
  const { docId } = useParams<{ docId: string }>();
  const navigate = useNavigate();
  const { documents, setCurrentDocument } = useDocumentStore();

  // 查找当前文档信息
  const document = documents.find((d) => d.doc_id === docId);

  const handleBack = () => {
    setCurrentDocument(null);
    navigate('/');
  };

  if (!docId) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-red-600">文档ID不存在</p>
      </div>
    );
  }

  return (
    <DocumentViewer
      docId={docId}
      filename={document?.filename}
      onBack={handleBack}
    />
  );
};
```

---

### 步骤8: 更新App.tsx集成路由

**文件**: `frontend/src/App.tsx`

```typescript
import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';

/**
 * PaperReader2 主应用
 */
const App: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default App;
```

---

### 步骤9: 添加样式

**文件**: `frontend/src/index.css`

在现有样式后添加：

```css
/* KaTeX样式 */
@import 'katex/dist/katex.min.css';

/* Markdown自定义样式 */
.prose {
  @apply text-gray-800 leading-relaxed;
}

.prose h1 {
  @apply text-3xl font-bold text-gray-900 mt-8 mb-4;
}

.prose h2 {
  @apply text-2xl font-semibold text-gray-900 mt-6 mb-3;
}

.prose h3 {
  @apply text-xl font-semibold text-gray-900 mt-4 mb-2;
}

.prose p {
  @apply my-4;
}

.prose ul,
.prose ol {
  @apply my-4 ml-6;
}

.prose ul {
  @apply list-disc;
}

.prose ol {
  @apply list-decimal;
}

.prose li {
  @apply my-2;
}

.prose blockquote {
  @apply border-l-4 border-gray-300 pl-4 italic my-4 text-gray-700;
}

.prose a {
  @apply text-blue-600 hover:text-blue-800 underline;
}

.prose table {
  @apply w-full my-4 border-collapse;
}

.prose table th,
.prose table td {
  @apply border border-gray-300 px-4 py-2;
}

.prose table th {
  @apply bg-gray-100 font-semibold;
}

.prose img {
  @apply max-w-full h-auto;
}

/* 数学公式样式 */
.katex-display {
  @apply my-6 overflow-x-auto;
}

.katex {
  @apply text-base;
}

/* 代码块样式 */
.prose code {
  @apply font-mono;
}

.prose pre code {
  @apply text-gray-100;
}
```

---

### 步骤10: 导出新组件

**文件**: `frontend/src/components/index.ts`

```typescript
export { FileUpload } from './FileUpload';
export { DocumentList } from './DocumentList';
export { Notification } from './Notification';

// 新增导出
export { MarkdownRenderer } from './MarkdownRenderer';
export { LazyImage } from './LazyImage';
export { LoadingSpinner } from './LoadingSpinner';
export { DocumentViewer } from './DocumentViewer';
```

---

## 🎯 开发阶段划分

### 阶段0: 类型修复（必须优先完成）⏱️ 2-3小时
**目标**: 修复前后端类型不匹配问题

**任务**:
1. ✅ 重构 `types/document.ts`，匹配后端API格式
2. ✅ 修复 `store/documentStore.ts`，调整字段映射
3. ✅ 测试上传和列表功能，确保状态正确显示

**验收**:
- 上传文档后，状态正确显示（不是永远是"处理中"）
- 文档列表正确显示所有字段
- 无TypeScript类型错误

---

### 阶段1: 基础设施 ⏱️ 3-4小时
**目标**: 搭建路由和基础组件

**任务**:
1. 安装依赖包
2. 配置路由系统
3. 更新 `App.tsx`
4. 创建 `HomePage.tsx`
5. 实现 `LoadingSpinner.tsx`

**验收**:
- 路由可以正常切换（首页 → 文档查看页）
- 加载动画正常显示

---

### 阶段2: 核心功能 ⏱️ 1天
**目标**: 实现Markdown渲染和图像懒加载

**任务**:
1. 实现 `LazyImage` 组件
2. 实现 `MarkdownRenderer` 组件
3. 添加样式到 `index.css`
4. 测试Markdown渲染和公式显示

**验收**:
- Markdown内容正确渲染
- 数学公式正确显示（行内和块级）
- 图像懒加载工作正常

---

### 阶段3: 状态管理 ⏱️ 半天
**目标**: 实现文档内容管理和轮询

**任务**:
1. 扩展 `documentStore.ts`（添加 `fetchDocumentContent`）
2. 实现 `useDocumentPolling` Hook
3. 测试轮询功能

**验收**:
- 可以获取文档内容
- 轮询自动检测状态变化
- 组件卸载时定时器正确清理

---

### 阶段4: 页面实现 ⏱️ 半天
**目标**: 实现文档查看页面

**任务**:
1. 实现 `DocumentViewer` 组件
2. 创建 `DocumentViewPage.tsx`
3. 测试完整查看流程

**验收**:
- 点击"查看"可导航到文档页面
- 正确显示文档内容
- 返回按钮工作
- 滚动进度正确显示

---

### 阶段5: 集成与优化 ⏱️ 半天
**目标**: 端到端测试和优化

**任务**:
1. 端到端测试：上传 → 轮询 → 查看
2. 集成轮询到 `DocumentList` 组件
3. 性能优化（大文档渲染）
4. 错误处理完善
5. 用户体验优化

**验收**:
- 完整流程无错误
- 大文档（50+页）渲染流畅
- 错误提示友好
- 无内存泄漏

---

## ⚠️ 关键注意事项

### 1. 类型一致性（最重要！）
**必须确保所有文件使用统一的状态类型**：

```typescript
// ✅ 正确（匹配后端）
status: 'processing' | 'ready' | 'error' | 'uploading'

// ❌ 错误（旧类型定义）
status: 'processing' | 'completed' | 'failed' | 'uploading'
```

**检查清单**：
- [ ] `types/document.ts` - 类型定义
- [ ] `store/documentStore.ts` - Store中使用
- [ ] `components/DocumentList.tsx` - 列表渲染
- [ ] `hooks/useDocumentPolling.ts` - 轮询逻辑

### 2. 图像路径处理
后端返回的Markdown中图像引用是文件名：
```markdown
![图片](img_001)
```

**必须转换为完整URL**：
```
http://localhost:8000/api/v1/documents/{docId}/images/img_001
```

### 3. 轮询资源管理
- **必须**在组件卸载时清理定时器
- 使用 `useRef` 保存定时器ID
- 避免重复轮询同一文档
- 使用指数退避策略减少服务器压力

### 4. 大文档性能优化
如果文档超过100页，考虑：
- 使用 `react-window` 虚拟滚动
- 分片加载章节
- 使用 `useMemo` 缓存渲染结果
- 延迟渲染非首屏内容

### 5. 错误处理
所有异步操作必须包含错误处理：
```typescript
try {
  const content = await fetchDocumentContent(docId);
  // ...
} catch (error) {
  console.error('加载文档失败:', error);
  setError(error instanceof Error ? error.message : '加载失败');
}
```

---

## 🧪 验收标准

### 功能验收
- ✅ 可以上传PDF文档
- ✅ 自动轮询检测处理状态（processing → ready）
- ✅ 处理完成后自动更新状态
- ✅ 点击"查看"可导航到文档页面
- ✅ 正确渲染Markdown内容
- ✅ 数学公式正确显示（行内 `$E=mc^2$` 和块级 `$$\int_0^\infty$$`）
- ✅ 图像懒加载正常工作
- ✅ 滚动进度正确显示（0-100%）
- ✅ 返回按钮可返回首页
- ✅ 错误处理完善（网络错误、加载失败）

### 性能验收
- ✅ 首次渲染时间 < 2秒
- ✅ Markdown渲染无明显卡顿（50页文档 < 1秒）
- ✅ 图像懒加载无性能问题
- ✅ 轮询不影响页面性能（CPU < 5%）
- ✅ 无内存泄漏（长时间使用不增长）

### 代码质量
- ✅ TypeScript无类型错误（`tsc --noEmit`）
- ✅ 遵循现有代码风格
- ✅ 组件职责单一（SRP）
- ✅ 无ESLint警告
- ✅ 所有新文件有导出和类型定义

---

## 📚 参考资料

### 项目文档
- **CLAUDE.md** - 架构模式和最佳实践
- **devplan.md** - Phase 2完整任务列表（行1258-1286）

### 外部文档
- [react-markdown文档](https://github.com/remarkjs/react-markdown)
- [KaTeX文档](https://katex.org/)
- [React Router v6文档](https://reactrouter.com/)
- [Intersection Observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)

---

## ✅ 下一步行动

执行此计划前，请确认：
1. ✅ 后端API已正常运行（`python -m app.main`）
2. ✅ 前端开发环境已就绪（`npm run dev`）
3. ✅ 已有测试PDF文档可用于测试
4. ✅ 已阅读并理解类型不匹配问题

**开始执行**：按照阶段0 → 阶段1 → ... → 阶段5的顺序实施。

**预计总工时**：3-4天
**关键里程碑**：
- 第1天：完成类型修复 + 基础设施
- 第2天：完成Markdown渲染和图像懒加载
- 第3天：完成状态轮询和文档查看页面
- 第4天：集成测试和优化

---

**祝开发顺利！🚀**
