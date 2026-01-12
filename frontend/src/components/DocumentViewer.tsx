/**
 * 文档查看器主组件
 */
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
