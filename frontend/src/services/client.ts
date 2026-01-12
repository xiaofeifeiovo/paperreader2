/**
 * Axios 客户端配置
 */
import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_PREFIX = '/api/v1';

/**
 * 创建 Axios 实例
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: `${API_BASE_URL}${API_PREFIX}`,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // 请求拦截器
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // 可以在这里添加认证 token
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 响应拦截器
  client.interceptors.response.use(
    (response) => {
      return response;
    },
    (error: AxiosError) => {
      // 统一错误处理
      if (error.response) {
        // 服务器返回错误响应
        console.error('API Error:', error.response.data);
      } else if (error.request) {
        // 请求发送但没有收到响应
        console.error('Network Error:', error.message);
      } else {
        // 请求配置出错
        console.error('Request Error:', error.message);
      }
      return Promise.reject(error);
    }
  );

  return client;
};

/**
 * 导出 API 客户端实例
 */
export const apiClient = createApiClient();

/**
 * 导出基础 URL 配置
 */
export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  PREFIX: API_PREFIX,
  FULL_URL: `${API_BASE_URL}${API_PREFIX}`,
};
