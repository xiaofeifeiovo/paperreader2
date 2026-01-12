/**
 * 侧边栏组件
 */
import React from 'react';
import { FileText, Upload } from 'lucide-react';
import { useDocumentStore } from '../store';

/**
 * 侧边栏
 */
const Sidebar: React.FC = () => {
  const { documents } = useDocumentStore();

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto">
      {/* 上传按钮区域 */}
      <div className="p-4 border-b border-gray-200">
        <button className="btn-primary w-full flex items-center justify-center space-x-2">
          <Upload className="w-5 h-5" />
          <span>上传文档</span>
        </button>
      </div>

      {/* 文档列表 */}
      <div className="p-4">
        <h2 className="text-sm font-semibold text-gray-600 mb-3">
          文档列表 ({documents.length})
        </h2>

        {documents.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            暂无文档
          </div>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.doc_id}
                className="group flex items-center p-3 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors duration-200"
              >
                <FileText className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {doc.filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <div className="ml-2">
                  <span
                    className={`inline-block px-2 py-1 text-xs rounded-full ${
                      doc.status === 'ready'
                        ? 'bg-green-100 text-green-700'
                        : doc.status === 'processing'
                        ? 'bg-yellow-100 text-yellow-700'
                        : doc.status === 'error'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {doc.status === 'ready' ? '已完成' : doc.status === 'processing' ? '处理中' : doc.status === 'error' ? '失败' : doc.status}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
