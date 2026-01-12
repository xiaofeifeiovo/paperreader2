# PaperReader2 前端

> 基于 React + Vite + TypeScript + Tailwind CSS 的现代化前端应用

## 技术栈

- **框架**: React 18.2.0
- **构建工具**: Vite 5.0.12
- **语言**: TypeScript 5.3.3
- **样式**: Tailwind CSS 3.4.1
- **状态管理**: Zustand 4.5.0
- **HTTP 客户端**: Axios 1.6.5
- **图标库**: Lucide React
- **Markdown 渲染**: react-markdown 9.0.1
- **公式渲染**: KaTeX 0.16.9

## 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件
│   │   ├── FileUpload.tsx   # 文件上传组件
│   │   ├── DocumentList.tsx # 文档列表组件
│   │   └── Notification.tsx # 通知组件
│   ├── layout/              # 布局组件
│   │   ├── MainLayout.tsx   # 主布局
│   │   ├── Header.tsx       # 顶部导航栏
│   │   └── Sidebar.tsx      # 侧边栏
│   ├── services/            # API 服务层
│   │   ├── client.ts        # Axios 客户端配置
│   │   ├── document.ts      # 文档 API
│   │   └── health.ts        # 健康 API
│   ├── store/               # Zustand 状态管理
│   │   ├── documentStore.ts # 文档状态
│   │   └── uiStore.ts       # UI 状态
│   ├── types/               # TypeScript 类型定义
│   │   ├── document.ts      # 文档类型
│   │   └── common.ts        # 通用类型
│   ├── hooks/               # 自定义 Hooks (待添加)
│   ├── utils/               # 工具函数 (待添加)
│   ├── App.tsx              # 主应用组件
│   ├── main.tsx             # 应用入口
│   └── index.css            # 全局样式
├── .env                     # 环境变量
├── .env.example             # 环境变量示例
├── tailwind.config.js       # Tailwind 配置
├── tsconfig.json            # TypeScript 配置
└── vite.config.ts           # Vite 配置
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 `http://localhost:5173` 查看应用。

### 4. 构建生产版本

```bash
npm run build
```

### 5. 预览生产构建

```bash
npm run preview
```

## 核心功能

### Phase 1 已实现

- ✅ React + Vite 项目搭建
- ✅ TypeScript 配置
- ✅ Tailwind CSS 样式系统
- ✅ 基础布局组件（Header, Sidebar, MainLayout）
- ✅ 文件上传组件（支持拖拽上传）
- ✅ 文档列表展示
- ✅ Axios API 服务层
- ✅ Zustand 状态管理
- ✅ 通知系统

### Phase 2-4 计划中

- ⏳ Markdown 渲染组件
- ⏳ KaTeX 公式渲染
- ⏳ 图像懒加载
- ⏳ AI 聊天界面
- ⏳ SSE 流式响应
- ⏳ 对话历史管理

## 组件使用示例

### 文件上传组件

```tsx
import { FileUpload } from './components';

function MyComponent() {
  return <FileUpload />;
}
```

### 文档列表组件

```tsx
import { DocumentList } from './components';

function MyComponent() {
  return <DocumentList />;
}
```

### API 服务调用

```typescript
import { documentService } from './services';

// 上传文档
const response = await documentService.uploadDocument(file);

// 获取文档列表
const list = await documentService.getDocumentList();

// 删除文档
await documentService.deleteDocument(docId);
```

### Zustand Store 使用

```typescript
import { useDocumentStore } from './store';

function MyComponent() {
  const { documents, uploadDocument, isLoading } = useDocumentStore();

  const handleUpload = async (file: File) => {
    await uploadDocument(file);
  };

  return (
    <div>
      {documents.map(doc => (
        <div key={doc.doc_id}>{doc.filename}</div>
      ))}
    </div>
  );
}
```

## 样式指南

### Tailwind CSS 自定义类

项目中定义了一些自定义 Tailwind 类：

- `.btn-primary` - 主要按钮样式
- `.btn-secondary` - 次要按钮样式
- `.card` - 卡片容器样式
- `.input` - 输入框样式
- `.upload-zone` - 文件上传区域样式

### 颜色系统

使用 Tailwind 的自定义颜色系统：

- `primary-50` 到 `primary-900` - 主题色（蓝色系）
- `gray-*` - 灰色系
- `green-*` - 成功状态
- `red-*` - 错误状态
- `yellow-*` - 警告状态

## 开发规范

### 组件开发

- 使用函数式组件 + Hooks
- 使用 TypeScript 定义 Props 类型
- 遵循单一职责原则
- 组件文件名使用 PascalCase

### 状态管理

- 使用 Zustand 进行全局状态管理
- 本地状态使用 `useState`
- 副作用使用 `useEffect`

### API 调用

- 所有 API 调用通过 `services` 层封装
- 使用 async/await 处理异步操作
- 统一错误处理

### 代码风格

- 使用 ESLint 进行代码检查
- 使用 Prettier 进行代码格式化
- 遵循 TypeScript 最佳实践

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 基础 URL | `http://127.0.0.1:8000` |

## 常见问题

### Q1: 样式不生效？

**A**: 确保已正确引入 `index.css` 并配置了 Tailwind CSS：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Q2: API 调用失败？

**A**: 检查：
1. 后端服务是否已启动
2. `.env` 文件中的 `VITE_API_BASE_URL` 是否正确
3. 浏览器控制台的网络请求

### Q3: TypeScript 类型错误？

**A**:
1. 确保已安装所有依赖：`npm install`
2. 检查 `types/` 目录下的类型定义
3. 使用 `npm run type-check` 检查类型

## 可用脚本

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 构建生产版本 |
| `npm run preview` | 预览生产构建 |
| `npm run lint` | 运行 ESLint |
| `npm run type-check` | TypeScript 类型检查 |

## 相关文档

- [Vite 文档](https://vitejs.dev/)
- [React 文档](https://react.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [Zustand 文档](https://zustand-demo.pmnd.rs/)
- [Axios 文档](https://axios-http.com/)
