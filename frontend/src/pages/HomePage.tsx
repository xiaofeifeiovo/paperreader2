/**
 * 首页组件
 */
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
