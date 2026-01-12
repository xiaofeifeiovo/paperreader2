/**
 * UI Store - Zustand 状态管理
 */
import { create } from 'zustand';

/**
 * UI 状态
 */
interface UIState {
  // 侧边栏状态
  isSidebarOpen: boolean;

  // 通知状态
  notification: {
    show: boolean;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
  } | null;

  // 操作方法
  toggleSidebar: () => void;
  openSidebar: () => void;
  closeSidebar: () => void;
  showNotification: (
    message: string,
    type: 'success' | 'error' | 'warning' | 'info'
  ) => void;
  hideNotification: () => void;
}

/**
 * 创建 UI Store
 */
export const useUIStore = create<UIState>((set) => ({
  // 初始状态
  isSidebarOpen: true,
  notification: null,

  // 切换侧边栏
  toggleSidebar: () => {
    set((state) => ({ isSidebarOpen: !state.isSidebarOpen }));
  },

  // 打开侧边栏
  openSidebar: () => {
    set({ isSidebarOpen: true });
  },

  // 关闭侧边栏
  closeSidebar: () => {
    set({ isSidebarOpen: false });
  },

  // 显示通知
  showNotification: (
    message: string,
    type: 'success' | 'error' | 'warning' | 'info' = 'info'
  ) => {
    set({ notification: { show: true, message, type } });

    // 3秒后自动隐藏
    setTimeout(() => {
      set({ notification: null });
    }, 3000);
  },

  // 隐藏通知
  hideNotification: () => {
    set({ notification: null });
  },
}));
