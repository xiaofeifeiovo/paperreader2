/**
 * Markdown渲染组件
 */
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkUnwrapImages from 'remark-unwrap-images';
import { LazyImage } from './LazyImage';
import { apiClient, API_CONFIG } from '../services/client';
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
        remarkPlugins={[remarkMath, remarkGfm, remarkUnwrapImages]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // 自定义图像组件（实现懒加载）
          img: ({ src, alt }) => {
            if (!src) {
              console.warn('⚠️ [MarkdownRenderer] 图片src为空,跳过渲染');
              return null;
            }

            console.log('🔍 [MarkdownRenderer] 处理图片:');
            console.log('  原始src:', src);
            console.log('  docId:', docId);

            // 处理相对路径转换为完整URL
            const getImageUrl = (src: string): string => {
              // 已经是完整的HTTP URL
              if (src.startsWith('http')) {
                console.log('  ✓ 检测到完整HTTP URL,直接使用');
                // ✅ 验证URL是否包含.png扩展名
                if (!src.endsWith('.png') && !src.includes('.')) {
                  const correctedUrl = `${src}.png`;
                  console.warn('  ⚠️ URL缺少.png扩展名,自动修正:', correctedUrl);
                  return correctedUrl;
                }
                return src;
              }

              // API路径 (以/api/开头): 需要添加base URL
              if (src.startsWith('/api/')) {
                console.log('  ✓ 检测到API路径,需要添加base URL');
                // ✅ 确保路径包含.png扩展名
                const imagePath = src.endsWith('.png') ? src : `${src}.png`;
                const fullUrl = `${API_CONFIG.BASE_URL}${imagePath}`;
                console.log('  🔄 转换为完整URL:', fullUrl);
                return fullUrl;
              }

              // 相对路径: 使用documentService转换
              if (docId) {
                console.log('  ✓ 检测到相对路径,使用documentService转换');
                const fullUrl = documentService.getImageUrl(docId, src);
                console.log('  🔄 转换为完整URL:', fullUrl);
                return fullUrl;
              }

              // 其他情况直接返回
              console.log('  ⚠️ 未知路径格式,直接返回:', src);
              return src;
            };

            const finalUrl = getImageUrl(src);

            console.log('  最终URL:', finalUrl);
            console.log('  是否为完整URL:', finalUrl.startsWith('http'));
            console.log('---');

            return (
              <LazyImage
                src={finalUrl}
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
