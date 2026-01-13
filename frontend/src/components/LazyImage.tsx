/**
 * 图像懒加载组件
 */
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

    // ✅ 增强日志: 记录详细的加载失败信息
    console.group('❌ [LazyImage] 图片加载失败');
    console.error('  🖼️ Alt文本:', alt);
    console.error('  🔗 图片URL:', src);
    console.error('  📄 当前页面URL:', window.location.href);
    console.error('  💡 可能的原因:');
    console.error('     1. URL缺少.png扩展名');
    console.error('     2. 后端图片文件不存在');
    console.error('     3. CORS配置问题');
    console.error('  🔍 调试建议:');
    console.error(`     - 直接访问URL验证: ${src}`);
    console.error(`     - 检查后端日志`);
    console.groupEnd();
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
