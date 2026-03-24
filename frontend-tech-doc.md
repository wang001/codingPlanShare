# LLM API聚合计费路由器前端技术方案

> **更新说明（2026-03-24）**：前端已整体重写，以下文档反映当前实际实现。

## 1. 技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | React | 18.2.0 | 函数组件 + Hooks |
| 构建工具 | Vite | 5.0.8 | 开发服务器 + 构建，配置 `/api` 和 `/admin` 代理 |
| UI 组件库 | Ant Design | 5.x | 响应式布局，PC 和移动端均可使用 |
| 路由 | React Router | 6.x | 声明式路由，支持嵌套路由和权限守卫 |
| HTTP 客户端 | Axios | 1.6.x | 统一请求拦截器，自动注入 token，401 跳转登录 |
| 语言 | TypeScript | 5.2.x | 全量类型覆盖 |
| 状态 | React useState/useEffect | - | 无全局状态管理库，组件本地状态 + API 直接调用 |

> **不使用**：Redux、ECharts、Formik、antd-mobile。UI 全部使用 antd 5 的响应式能力，无需额外移动端库。

---

## 2. 项目结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts              # 代理 /api 和 /admin 到 http://localhost:3000
└── src/
    ├── main.tsx                # 入口
    ├── App.tsx                 # 路由配置 + 权限守卫
    ├── index.css               # 全局样式
    ├── api/                    # API 请求模块
    │   ├── axios.ts            # axios 实例 + 拦截器
    │   ├── auth.ts             # 登录接口
    │   ├── users.ts            # 用户接口
    │   ├── keys.ts             # 密钥接口
    │   ├── points.ts           # 积分接口
    │   └── admin.ts            # 管理员接口
    ├── layouts/
    │   ├── UserLayout.tsx      # 普通用户侧边栏布局
    │   └── AdminLayout.tsx     # 管理员侧边栏布局
    ├── pages/
    │   ├── LoginPage.tsx       # 登录页（用户/管理员 Tab 切换）
    │   ├── HomePage.tsx        # 首页（积分余额 + 快捷入口）
    │   ├── PointsPage.tsx      # 积分页（余额 + 明细列表）
    │   ├── KeysPage.tsx        # 密钥页（平台密钥 + 厂商密钥）
    │   ├── StatsPage.tsx       # 统计页（积分日志）
    │   └── admin/
    │       ├── AdminDashboard.tsx  # 管理控制台
    │       ├── AdminUsers.tsx      # 用户管理
    │       ├── AdminKeys.tsx       # 密钥管理
    │       └── AdminLogs.tsx       # 调用日志
    ├── types/
    │   └── index.ts            # 全局类型定义
    └── utils/
        └── index.ts            # 工具函数（时间格式化等）
```

---

## 3. 认证与授权机制

### 3.1 Token 存储

登录成功后，将 `access_token` 存入 `localStorage`：

| key | 内容 |
|-----|------|
| `user_token` | 普通用户 JWT |
| `admin_token` | 管理员 JWT |

### 3.2 Axios 拦截器（`src/api/axios.ts`）

- **请求拦截**：根据请求 URL 前缀自动选择 token（`/admin/*` 用 `admin_token`，其余用 `user_token`），注入 `Authorization: Bearer <token>` header
- **响应拦截**：收到 401 时清除对应 token 并跳转到 `/login`

### 3.3 路由权限守卫（`src/App.tsx`）

| 守卫组件 | 逻辑 |
|----------|------|
| `UserGuard` | 检查 `user_token`，无则跳 `/login` |
| `AdminGuard` | 检查 `admin_token`，无则跳 `/login` |

---

## 4. 路由设计

```
/login                  # 登录页（用户/管理员 Tab 切换）

# 普通用户（需要 user_token）
/                       # 首页：用户名、积分余额、快捷入口
/points                 # 积分页：余额 + 明细
/keys                   # 密钥页：平台密钥 / 厂商密钥管理
/stats                  # 统计页：积分日志查看

# 管理员（需要 admin_token）
/admin                  # 控制台概览
/admin/users            # 用户管理：列表 / 创建 / 状态 / 积分调整
/admin/keys             # 密钥管理：所有密钥 / 状态管理
/admin/logs             # 调用日志
```

---

## 5. API 对接

所有接口均连接真实后端（FastAPI），无 mock 数据。

### 5.1 用户端接口

| 接口 | 用途 |
|------|------|
| `POST /api/v1/auth/login` | 用户登录 |
| `GET /api/v1/users/me` | 获取当前用户信息（包含余额） |
| `GET /api/v1/points` | 获取积分余额 |
| `GET /api/v1/points/logs` | 获取积分明细（分页） |
| `GET /api/v1/keys` | 获取密钥列表 |
| `POST /api/v1/keys` | 创建密钥 |
| `PUT /api/v1/keys/{id}` | 更新密钥 |
| `DELETE /api/v1/keys/{id}` | 删除密钥 |

### 5.2 管理员接口（需要管理员 token）

| 接口 | 用途 |
|------|------|
| `POST /api/v1/auth/admin/login` | 管理员登录 |
| `GET /admin/users` | 用户列表 |
| `POST /admin/users` | 创建用户 |
| `PUT /admin/users/{id}` | 更新用户状态 |
| `POST /admin/points` | 调整用户积分 |
| `GET /admin/keys` | 所有密钥列表 |
| `PUT /admin/keys/{id}` | 更新密钥状态 |
| `DELETE /admin/keys/{id}` | 删除密钥 |
| `GET /admin/logs` | 调用日志（分页） |

---

## 6. 响应式设计方案

使用 antd 5 的 `Row/Col` 栅格系统和 `Flex` 布局，实现 PC 和手机的自适应：

- **PC 端**：侧边栏导航（`UserLayout` / `AdminLayout`），内容区宽屏展示
- **移动端**：侧边栏折叠为 `Drawer` 抽屉，顶部 hamburger 菜单触发
- **卡片/表格**：在小屏幕（xs）下自动转为单列或横向滚动

---

## 7. 数据枚举映射

### 密钥类型（`key_type`）

| 值 | 含义 |
|----|------|
| 1 | 平台调用密钥 |
| 2 | 厂商托管密钥 |

### 密钥状态（`status`）

| 值 | 含义 |
|----|------|
| 0 | 正常 |
| 1 | 已删除 |
| 2 | 已禁用 |
| 3 | 超限 |
| 4 | 无效 |

### 积分变动类型（`type`）

| 值 | 含义 |
|----|------|
| 1 | 调用消耗 |
| 2 | 托管收益 |
| 3 | 管理员调整 |
| 4 | 平台收入 |

---

## 8. 开发与部署

### 8.1 本地开发

```bash
cd frontend
npm install
npm run dev          # 启动开发服务器，代理后端到 http://localhost:3000
```

### 8.2 vite.config.ts 代理配置

```ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:3000', changeOrigin: true },
    '/admin': { target: 'http://localhost:3000', changeOrigin: true },
  }
}
```

### 8.3 生产构建

```bash
npm run build        # 输出到 frontend/dist/
```

构建产物可直接由后端 FastAPI 通过 `StaticFiles` 挂载，或独立部署到 Nginx / CDN。

---

## 9. 安全性

- JWT token 存于 `localStorage`，刷新页面不丢失
- 所有写操作（创建/删除/更新）均需有效 token，后端统一鉴权
- axios 拦截器在 401 时自动清除 token 并跳转登录，防止过期 token 继续使用
- 管理员 token 与普通用户 token 完全隔离，互不干扰

---

## 10. 主要依赖版本

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "antd": "^5.12.8",
    "axios": "^1.6.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```
