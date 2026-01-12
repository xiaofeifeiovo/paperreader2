/**
 * Markdown渲染组件
 */
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
    <div className={`prose prose-lg max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // 自定义图像组件（实现懒加载）
          img: ({ src, alt }) => {
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
          code: ({ className, children }) => {
            const isInline = !className?.includes('language-');

            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 bg-gray-100 text-red-600 rounded text-sm font-mono"
                >
                  {children}
                </code>
              );
            }

            return (
              <code
                className={`block bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono ${className || ''}`}
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
    </div>
  );
};
