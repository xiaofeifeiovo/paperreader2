/**
 * 路由配置
 */
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { MainLayout } from '../layout';
import { HomePage } from '../pages/HomePage';
import { DocumentViewPage } from '../pages/DocumentViewPage';

/**
 * 布局包装器：渲染 MainLayout 和 Outlet
 */
const LayoutWrapper = () => (
  <MainLayout>
    <Outlet />
  </MainLayout>
);

/**
 * 路由配置
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <LayoutWrapper />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'document/:docId',
        element: <DocumentViewPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
