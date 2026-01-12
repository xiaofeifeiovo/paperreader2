/**
 * PaperReader2 主应用
 */
import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';

/**
 * 主应用组件
 */
const App: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default App;
