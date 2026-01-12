/**
 * 健康 API 服务
 */
import { apiClient } from './client';
import type { HealthResponse } from '../types';

/**
 * 健康服务类
 */
class HealthService {
  private readonly basePath = '/health';

  /**
   * 健康检查
   * @returns 健康状态
   */
  async check(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>(this.basePath);
    return response.data;
  }

  /**
   * Ping 检查
   * @returns ping 响应
   */
  async ping(): Promise<{ message: string }> {
    const response = await apiClient.get<{ message: string }>(
      `${this.basePath}/ping`
    );
    return response.data;
  }
}

/**
 * 导出健康服务单例
 */
export const healthService = new HealthService();
