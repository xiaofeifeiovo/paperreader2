/**
 * 文档状态轮询Hook
 */
import { useEffect, useState, useRef } from 'react';
import type { DocumentStatus } from '../types';
import { documentService } from '../services';

interface UseDocumentPollingOptions {
  docId: string;
  initialStatus?: DocumentStatus;
  interval?: number;           // 轮询间隔（毫秒）
  maxAttempts?: number;        // 最大轮询次数
  onStatusChange?: (status: DocumentStatus) => void;
  onComplete?: () => void;     // 处理完成回调
  onError?: (error: string) => void; // 处理失败回调
}

interface UseDocumentPollingReturn {
  status: DocumentStatus;
  isPolling: boolean;
  pollingCount: number;
  stopPolling: () => void;
}

/**
 * 文档状态轮询Hook
 *
 * 特性：
 * - 指数退避策略（3s → 5s → 10s）
 * - 自动停止条件（ready/error）
 * - 组件卸载时自动清理
 */
export const useDocumentPolling = ({
  docId,
  initialStatus = 'processing' as DocumentStatus,
  interval = 3000,
  maxAttempts = 100,  // 约5分钟
  onStatusChange,
  onComplete,
  onError,
}: UseDocumentPollingOptions): UseDocumentPollingReturn => {
  const [status, setStatus] = useState<DocumentStatus>(initialStatus);
  const [pollingCount, setPollingCount] = useState(0);
  const intervalRef = useRef<number | undefined>(undefined);

  // 计算动态轮询间隔（指数退避）
  const calculateInterval = (count: number): number => {
    if (count < 10) return 3000;      // 前10次：每3秒
    if (count < 30) return 5000;      // 10-30次：每5秒
    return 10000;                     // 30次后：每10秒
  };

  // 停止轮询
  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = undefined;
    }
  };

  // 轮询逻辑
  useEffect(() => {
    // 如果初始状态已经是最终状态，不启动轮询
    if (initialStatus === 'ready' || initialStatus === 'error') {
      return;
    }

    const poll = async () => {
      try {
        const doc = await documentService.getDocument(docId);
        const newStatus = doc.status;

        setStatus(newStatus);
        setPollingCount((prev) => {
          const newCount = prev + 1;
          onStatusChange?.(newStatus);

          // 检查停止条件
          if (newStatus === 'ready') {
            stopPolling();
            onComplete?.();
          } else if (newStatus === 'error') {
            stopPolling();
            onError?.('文档处理失败');
          } else if (newCount >= maxAttempts) {
            stopPolling();
            onError?.('文档处理超时');
          }

          return newCount;
        });

        // 动态调整间隔（指数退避）
        stopPolling();
        const nextInterval = calculateInterval(pollingCount);
        intervalRef.current = setInterval(poll, nextInterval);
      } catch (error) {
        stopPolling();
        onError?.(error instanceof Error ? error.message : '获取文档状态失败');
      }
    };

    // 启动轮询
    intervalRef.current = setInterval(poll, interval);

    // 清理函数
    return () => stopPolling();
  }, [docId, initialStatus]);

  return {
    status,
    isPolling: !!intervalRef.current,
    pollingCount,
    stopPolling,
  };
};
