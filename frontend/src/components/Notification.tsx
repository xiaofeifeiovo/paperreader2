/**
 * 通知组件
 */
import React, { useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import { useUIStore } from '../store';

/**
 * 通知组件
 */
const Notification: React.FC = () => {
  const { notification, hideNotification } = useUIStore();

  useEffect(() => {
    if (notification?.show) {
      // 3秒后自动隐藏
      const timer = setTimeout(() => {
        hideNotification();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [notification, hideNotification]);

  if (!notification?.show) {
    return null;
  }

  // 根据类型选择图标和样式
  const getIconAndStyle = () => {
    switch (notification.type) {
      case 'success':
        return {
          icon: <CheckCircle className="w-6 h-6" />,
          bgColor: 'bg-green-50',
          borderColor: 'border-green-500',
          textColor: 'text-green-800',
        };
      case 'error':
        return {
          icon: <XCircle className="w-6 h-6" />,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-500',
          textColor: 'text-red-800',
        };
      case 'warning':
        return {
          icon: <AlertCircle className="w-6 h-6" />,
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-500',
          textColor: 'text-yellow-800',
        };
      case 'info':
      default:
        return {
          icon: <Info className="w-6 h-6" />,
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-500',
          textColor: 'text-blue-800',
        };
    }
  };

  const { icon, bgColor, borderColor, textColor } = getIconAndStyle();

  return (
    <div className="fixed top-20 right-6 z-50 animate-slide-in">
      <div
        className={`${bgColor} ${borderColor} ${textColor} border-l-4 rounded-lg shadow-lg p-4 flex items-start space-x-3 min-w-[300px] max-w-md`}
      >
        <div className={`${textColor} flex-shrink-0`}>{icon}</div>
        <div className="flex-1">
          <p className="font-medium">{notification.message}</p>
        </div>
        <button
          onClick={hideNotification}
          className={`${textColor} hover:opacity-70 transition-opacity duration-200`}
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default Notification;
