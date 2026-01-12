/**
 * 文档相关类型定义
 * ⚠️ 必须与后端API返回格式完全匹配
 */

/**
 * 文档状态枚举
 * 对应后端: app/api/v1/documents.py
 */
export const DocumentStatus = {
  UPLOADING: 'uploading',    // 前端本地状态（上传中）
  PROCESSING: 'processing',  // 后端返回（处理中）
  READY: 'ready',           // 后端返回（处理完成）✅ 修复
  ERROR: 'error',           // 后端返回（处理失败）
} as const;

export type DocumentStatus = (typeof DocumentStatus)[keyof typeof DocumentStatus];

/**
 * 文档信息（来自列表API）
 * 对应后端: GET /api/v1/documents/list
 */
export interface Document {
  doc_id: string;
  filename: string;
  status: DocumentStatus;
  upload_time: number;      // ✅ 修复: Unix时间戳（浮点数）
  file_size: number;
}

/**
 * 文档上传响应
 * 对应后端: POST /api/v1/documents/upload
 */
export interface UploadResponse {
  doc_id: string;
  filename: string;
  status: DocumentStatus;
  message: string;
  file_size: number;
}

/**
 * 文档内容（来自详情API）
 * 对应后端: GET /api/v1/documents/{doc_id}
 */
export interface DocumentContent {
  doc_id: string;
  content: string;         // ✅ 修复: 后端字段名是 content
  images: string[];        // 图像文件名列表，如 ["img_001", "img_002"]
  status: DocumentStatus;
}

/**
 * 文档列表响应
 * 对应后端: GET /api/v1/documents/list
 */
export interface DocumentListResponse {
  documents: Document[];
  total?: number;
}

/**
 * API 错误响应
 */
export interface ApiError {
  detail: string;
  status_code?: number;
}

/**
 * 健康检查响应
 */
export interface HealthResponse {
  status: string;
  timestamp: string;
}
