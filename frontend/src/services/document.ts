/**
 * 文档 API 服务
 */
import { apiClient } from './client';
import type {
  DocumentContent,
  DocumentListResponse,
  UploadResponse,
} from '../types';

/**
 * 文档服务类
 */
class DocumentService {
  private readonly basePath = '/documents';

  /**
   * 上传文档
   * @param file 文件对象
   * @returns 上传响应
   */
  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>(
      `${this.basePath}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * 获取文档列表
   * @returns 文档列表
   */
  async getDocumentList(): Promise<DocumentListResponse> {
    const response = await apiClient.get<DocumentListResponse>(
      `${this.basePath}/list`
    );

    return response.data;
  }

  /**
   * 获取文档内容
   * @param docId 文档 ID
   * @returns 文档内容
   */
  async getDocument(docId: string): Promise<DocumentContent> {
    const response = await apiClient.get<DocumentContent>(
      `${this.basePath}/${docId}`
    );

    return response.data;
  }

  /**
   * 获取文档图像 URL
   * @param docId 文档 ID
   * @param imageName 图像名称
   * @returns 图像 URL
   */
  getImageUrl(docId: string, imageName: string): string {
    return `${apiClient.defaults.baseURL}${this.basePath}/${docId}/images/${imageName}`;
  }

  /**
   * 删除文档
   * @param docId 文档 ID
   * @returns 删除结果
   */
  async deleteDocument(docId: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(
      `${this.basePath}/${docId}`
    );

    return response.data;
  }
}

/**
 * 导出文档服务单例
 */
export const documentService = new DocumentService();
