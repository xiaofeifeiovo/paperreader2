/**
 * 文档列表组件
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Trash2, Eye } from 'lucide-react';
import { useDocumentStore } from '../store';
import { DocumentStatus } from '../types';

/**
 * 文档列表组件
 */
const DocumentList: React.FC = () => {
  const navigate = useNavigate();
  const { documents, isLoading, error, fetchDocuments, deleteDocument } =
    useDocumentStore();

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  /**
   * 获取状态标签样式
   */
  const getStatusBadge = (status: DocumentStatus) => {
    const styles = {
      [DocumentStatus.UPLOADING]: 'bg-blue-100 text-blue-700',
      [DocumentStatus.PROCESSING]: 'bg-yellow-100 text-yellow-700',
      [DocumentStatus.READY]: 'bg-green-100 text-green-700',  // ✅ 修复
      [DocumentStatus.ERROR]: 'bg-red-100 text-red-700',      // ✅ 修复
    };

    const labels = {
      [DocumentStatus.UPLOADING]: '上传中',
      [DocumentStatus.PROCESSING]: '处理中',
      [DocumentStatus.READY]: '已完成',   // ✅ 修复
      [DocumentStatus.ERROR]: '失败',     // ✅ 修复
    };

    return (
      <span
        className={`px-2 py-1 text-xs rounded-full ${styles[status] || styles[DocumentStatus.PROCESSING]}`}
      >
        {labels[status] || status}
      </span>
    );
  };

  /**
   * 处理删除文档
   */
  const handleDelete = async (docId: string, filename: string) => {
    if (window.confirm(`确定要删除 "${filename}" 吗？`)) {
      try {
        await deleteDocument(docId);
      } catch (error) {
        console.error('删除文档失败:', error);
      }
    }
  };

  /**
   * 处理查看文档
   */
  const handleViewDocument = (docId: string) => {
    navigate(`/document/${docId}`);
  };

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-4 text-gray-600">加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">暂无文档</p>
        <p className="text-sm text-gray-400 mt-2">
          请先上传 PDF 或 DOCX 文件
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-800">文档列表</h2>

      <div className="grid gap-4">
        {documents.map((doc) => (
          <div
            key={doc.doc_id}
            className="card hover:shadow-lg transition-shadow duration-200"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4 flex-1">
                <FileText className="w-12 h-12 text-primary-500 flex-shrink-0 mt-1" />
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-800 truncate">
                    {doc.filename}
                  </h3>
                  <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                    <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                    <span>•</span>
                    <span>
                      {new Date(doc.upload_time * 1000).toLocaleString('zh-CN')}  {/* ✅ 修复：Unix时间戳转日期 */}
                    </span>
                  </div>
                  <div className="mt-2">{getStatusBadge(doc.status)}</div>
                </div>
              </div>

              <div className="flex items-center space-x-2 ml-4">
                {/* ✅ 修复：READY状态才显示查看按钮 */}
                {doc.status === DocumentStatus.READY && (
                  <button
                    onClick={() => handleViewDocument(doc.doc_id)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
                    title="查看文档"
                  >
                    <Eye className="w-5 h-5 text-gray-600" />
                  </button>
                )}
                <button
                  onClick={() => handleDelete(doc.doc_id, doc.filename)}
                  className="p-2 hover:bg-red-50 rounded-lg transition-colors duration-200"
                  title="删除文档"
                >
                  <Trash2 className="w-5 h-5 text-red-600" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocumentList;
