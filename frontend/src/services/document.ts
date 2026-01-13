/**
 * 文档 API 服务
 */
import { apiClient } from './client';
import type {
  ConverterType,
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
   * ✅ 修改：添加converter参数
   *
   * @param file 文件对象
   * @param converter PDF转换器类型 (默认: pix2text)
   * @returns 上传响应
   */
  async uploadDocument(
    file: File,
    converter: ConverterType = 'pix2text'
  ): Promise<UploadResponse> {
    // 🔍 调试日志：接收参数
    console.log('🔍 [documentService] ===== uploadDocument 被调用 =====');
    console.log('🔍 [documentService] 接收到的 converter:', converter);
    console.log('🔍 [documentService] converter 类型:', typeof converter);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('converter', converter);  // ✅ 添加converter字段

    // 🔍 调试日志：验证 FormData 内容
    console.log('🔍 [documentService] FormData entries:');
    for (let [key, value] of Array.from(formData.entries())) {
      console.log(`  - ${key}:`, value);
    }

    const response = await apiClient.post<UploadResponse>(
      `${this.basePath}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    console.log('✅ [documentService] API 响应:', response.data);
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
    // ✅ 确保 imageName 包含 .png 扩展名
    const imageNameWithExt = imageName.endsWith('.png')
      ? imageName
      : `${imageName}.png`;

    const url = `${apiClient.defaults.baseURL}${this.basePath}/${docId}/images/${imageNameWithExt}`;

    // 🔍 调试日志: 记录图片URL构建过程
    console.log('🔍 [DocumentService] 构建图片URL:');
    console.log('  原始 imageName:', imageName);
    console.log('  修正后 imageName:', imageNameWithExt);
    console.log('  baseURL:', apiClient.defaults.baseURL);
    console.log('  最终 URL:', url);

    return url;
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
