/**
 * 文档查看页面
 */
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
