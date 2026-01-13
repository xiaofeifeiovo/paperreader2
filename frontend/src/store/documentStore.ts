/**
 * 文档 Store - Zustand 状态管理
 */
import { create } from 'zustand';
import type { ConverterType, Document, DocumentContent } from '../types';
import { documentService } from '../services';

/**
 * 文档 Store 状态
 */
interface DocumentState {
  // 状态数据
  documents: Document[];
  currentDocument: Document | null;
  currentDocumentContent: DocumentContent | null;  // ✅ 新增
  isLoading: boolean;
  error: string | null;

  // 操作方法
  fetchDocuments: () => Promise<void>;
  fetchDocumentContent: (docId: string) => Promise<DocumentContent>;  // ✅ 新增
  uploadDocument: (file: File, converter?: ConverterType) => Promise<string>;  // ✅ 修改：添加converter参数
  deleteDocument: (docId: string) => Promise<void>;
  setCurrentDocument: (document: Document | null) => void;
  clearError: () => void;
}

/**
 * 创建文档 Store
 */
export const useDocumentStore = create<DocumentState>((set) => ({
  // 初始状态
  documents: [],
  currentDocument: null,
  currentDocumentContent: null,  // ✅ 新增
  isLoading: false,
  error: null,

  // 获取文档列表
  fetchDocuments: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await documentService.getDocumentList();
      set({ documents: response.documents, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '获取文档列表失败',
        isLoading: false,
      });
    }
  },

  // ✅ 新增：获取文档内容
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

  // 上传文档
  // ✅ 修改：添加converter参数
  uploadDocument: async (file: File, converter: ConverterType = 'pix2text') => {
    // 🔍 调试日志：接收参数
    console.log('🔍 [documentStore] ===== uploadDocument 被调用 =====');
    console.log('🔍 [documentStore] 接收到的 converter:', converter);
    console.log('🔍 [documentStore] 文件信息:', file.name, file.size);

    set({ isLoading: true, error: null });
    try {
      const response = await documentService.uploadDocument(file, converter);  // ✅ 传递converter

      console.log('✅ [documentStore] API 响应成功:', response);

      // ✅ 修复：创建临时文档对象（匹配后端格式）
      const newDoc: Document = {
        doc_id: response.doc_id,
        filename: response.filename,
        file_size: response.file_size,  // 使用后端返回的大小
        status: response.status,
        upload_time: Date.now() / 1000,  // ✅ Unix时间戳（浮点数）
      };

      // 添加到文档列表
      set((state) => ({
        documents: [newDoc, ...state.documents],
        isLoading: false,
      }));

      return response.doc_id;
    } catch (error) {
      console.error('❌ [documentStore] 上传失败:', error);
      set({
        error: error instanceof Error ? error.message : '上传文档失败',
        isLoading: false,
      });
      throw error;
    }
  },

  // 删除文档
  deleteDocument: async (docId: string) => {
    set({ isLoading: true, error: null });
    try {
      await documentService.deleteDocument(docId);

      // 从文档列表中移除
      set((state) => ({
        documents: state.documents.filter((doc) => doc.doc_id !== docId),
        currentDocument:
          state.currentDocument?.doc_id === docId
            ? null
            : state.currentDocument,
        currentDocumentContent:
          state.currentDocumentContent?.doc_id === docId
            ? null
            : state.currentDocumentContent,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '删除文档失败',
        isLoading: false,
      });
      throw error;
    }
  },

  // 设置当前文档
  setCurrentDocument: (document: Document | null) => {
    set({ currentDocument: document });
  },

  // 清除错误
  clearError: () => {
    set({ error: null });
  },
}));
