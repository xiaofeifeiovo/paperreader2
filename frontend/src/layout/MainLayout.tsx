/**
 * 主布局组件
 */
import React from 'react';
import type { ReactNode } from 'react';
import { useUIStore } from '../store';
import Header from './Header';
import Sidebar from './Sidebar';
import Notification from '../components/Notification';

interface MainLayoutProps {
  children: ReactNode;
}

/**
 * 主布局
 */
const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { isSidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <Header />

      {/* 主体内容区域 */}
      <div className="flex">
        {/* 侧边栏 */}
        <aside
          className={`bg-white shadow-lg transition-all duration-300 ${
            isSidebarOpen ? 'w-64' : 'w-0'
          } overflow-hidden`}
        >
          <Sidebar />
        </aside>

        {/* 主内容区域 */}
        <main className="flex-1 p-6">{children}</main>
      </div>

      {/* 通知组件 */}
      <Notification />
    </div>
  );
};

export default MainLayout;
