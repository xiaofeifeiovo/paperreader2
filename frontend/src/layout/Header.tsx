/**
 * 顶部导航栏组件
 */
import React from 'react';
import { Menu } from 'lucide-react';
import { useUIStore } from '../store';

/**
 * 顶部导航栏
 */
const Header: React.FC = () => {
  const { toggleSidebar } = useUIStore();

  return (
    <header className="bg-white shadow-md h-16 flex items-center px-6 fixed top-0 left-0 right-0 z-10">
      {/* 侧边栏切换按钮 */}
      <button
        onClick={toggleSidebar}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200 mr-4"
        aria-label="Toggle sidebar"
      >
        <Menu className="w-6 h-6 text-gray-600" />
      </button>

      {/* Logo 和标题 */}
      <div className="flex items-center">
        <h1 className="text-xl font-bold text-gray-800">PaperReader2</h1>
        <span className="ml-2 px-2 py-1 bg-primary-100 text-primary-700 text-xs rounded-full">
          AI 增强型论文阅读器
        </span>
      </div>

      {/* 右侧工具栏 */}
      <div className="ml-auto flex items-center space-x-4">
        {/* 可以添加用户信息、设置等按钮 */}
        <div className="text-sm text-gray-600">
          本地部署模式
        </div>
      </div>
    </header>
  );
};

export default Header;
