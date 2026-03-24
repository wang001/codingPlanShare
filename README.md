<div align="center">

# 🔀 LLM Router

**一个轻量级的 LLM API 聚合计费网关**

把你手里闲置的 API 额度变成收益，让大家都能低成本用上好模型。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

</div>

---

## 💡 这是什么？

很多开发者手里都有闲置的 LLM 厂商 API 额度——充了会员用不完、公司采购了没怎么用。与此同时，另一批开发者需要调用各种模型，但不想对接十几家厂商的不同接口。

**LLM Router** 就是连接这两类人的桥梁：

- **托管者**：把你的厂商密钥托管到平台，每次被调用时自动获得积分收益
- **调用者**：用一个统一的 OpenAI 兼容接口，消耗积分调用多家厂商的模型
- **平台**：从中抽取少量差价维持运营

整个系统完全开源，你可以自己搭一个给团队用，也可以对外运营。

## ✨ 核心特性

- 🔌 **OpenAI 兼容接口** — 无需改动现有代码，把 `base_url` 换成自己部署的地址就行
- 🏦 **积分计费** — 预扣 + 确认的双阶段计费，失败自动回滚，不多扣一分
- 🔑 **密钥池路由** — 自动选择可用密钥，失效自动重试，对调用方透明
- 🛡️ **SSRF 防护** — 厂商 URL 白名单机制，只允许访问已知的合法厂商地址
- 📊 **管理后台** — 用户管理、密钥管理、积分调整、调用日志，全套可视化
- 📱 **响应式 UI** — 手机和电脑都能正常使用

## 🏗️ 支持的厂商

| Provider | 模型示例 | 调用前缀 |
|----------|----------|----------|
| ModelScope | moonshotai/Kimi-K2.5、Qwen 系列等 | `modelscope/` |
| 智谱 AI | GLM-4 | `zhipu/` |
| MiniMax | abab6.5 | `minimax/` |
| 阿里云百炼 | qwen-turbo | `alibaba/` |
| 腾讯混元 | hunyuan-pro | `tencent/` |
| 百度千帆 | ernie-4.0 | `baidu/` |
| DeepSeek | deepseek-chat | `deepseek/` |
| SiliconFlow | 多种开源模型 | `siliconflow/` |

> 调用示例：`model: "modelscope/moonshotai/Kimi-K2.5"` — 第一段是 provider，后面是真实模型名。

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+

### 1. 克隆仓库

```bash
git clone https://github.com/wang001/codingPlanShare.git
cd codingPlanShare
```

### 2. 启动后端

```bash
# 安装依赖（国内用户推荐加镜像源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 初始化数据库
python init_db.py

# 启动服务（默认端口 3000）
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

访问 http://localhost:3000/docs 查看自动生成的 API 文档。

### 3. 启动前端

```bash
cd frontend

# 安装依赖（国内用户推荐加镜像源）
npm install --include=dev --registry https://registry.npmmirror.com

# 开发模式启动
npm run dev
```

访问 http://localhost:5173 打开管理界面。

### 4. 初始登录

| 角色 | 方式 |
|------|------|
| 普通用户 | 邮箱 `admin@example.com`，密码 `admin123` |
| 管理员 | 管理员密码 `admin123`（在登录页切换到「管理员登录」Tab） |

> ⚠️ **首次部署后请立即修改 `config.yaml` 中的密码和密钥！**

### 5. 开始使用

1. 以管理员身份登录，创建用户
2. 以用户身份登录，在「密钥」页面托管你的厂商 API 密钥（如 ModelScope 密钥）
3. 创建一个平台调用密钥
4. 用该平台密钥调用 API：

```python
from openai import OpenAI

client = OpenAI(
    api_key="你的平台密钥",
    base_url="http://localhost:3000/api/v1/chat",
)

response = client.chat.completions.create(
    model="modelscope/moonshotai/Kimi-K2.5",
    messages=[{"role": "user", "content": "你好！"}]
)
print(response.choices[0].message.content)
```

> **注意**：请求头使用 `api-key` 而非 `Authorization`（标准 OpenAI SDK 会自动处理）。

---

## ⚙️ 配置说明

编辑 `config.yaml` 完成个性化配置：

```yaml
# 管理员配置
admin:
  password: "your-strong-password"   # 修改为强密码

# 加密配置（生产环境必须修改）
security:
  encryption_key: "your-32-char-encryption-key"
  jwt_secret: "your-jwt-secret"

# 数据库
database:
  driver: "sqlite"
  path: "./data/app.db"

# 限流
rate_limit:
  user_rpm: 60          # 单用户每分钟最大请求数
  default_provider_rpm: 30

# 超时
timeout:
  request_timeout: 30   # 单位：秒
```

---

## 🐳 Docker 部署

```bash
docker build -t llm-router .
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  llm-router
```

---

## 📁 项目结构

```
codingPlanShare/
├── app/
│   ├── api/            # HTTP 接口层（auth/users/keys/points/chat/admin）
│   ├── services/       # 业务逻辑（认证/积分/密钥/路由/管理）
│   ├── providers/      # 厂商适配器（统一 OpenAI 兼容格式）
│   ├── models/         # 数据库模型
│   ├── schemas/        # 请求/响应结构
│   ├── utils/          # 工具（加密/缓存/后台任务）
│   └── main.py         # 应用入口
├── frontend/
│   └── src/
│       ├── api/        # 接口请求封装（含 axios 拦截器）
│       ├── layouts/    # 用户端/管理员端布局
│       └── pages/      # 页面组件
├── config.yaml         # 配置文件
├── init_db.py          # 数据库初始化
└── requirements.txt
```

---

## 🔌 API 接口速览

### 用户端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/users/me` | 获取当前用户信息 |
| GET/POST | `/api/v1/keys` | 密钥列表 / 创建密钥 |
| PUT/DELETE | `/api/v1/keys/{id}` | 更新 / 删除密钥 |
| GET | `/api/v1/points` | 积分余额 |
| GET | `/api/v1/points/logs` | 积分明细 |
| POST | `/api/v1/chat/completions` | 对话接口（需 `api-key` header） |
| POST | `/api/v1/embeddings` | 嵌入接口 |

### 管理员端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/admin/login` | 管理员登录 |
| GET/POST | `/api/admin/users` | 用户列表 / 创建用户 |
| PUT | `/api/admin/users/{id}` | 更新用户状态 |
| POST | `/api/admin/points` | 调整用户积分 |
| GET | `/api/admin/keys` | 所有密钥列表 |
| PUT/DELETE | `/api/admin/keys/{id}` | 管理密钥状态 |
| GET | `/api/admin/logs` | 调用日志 |

---

## 🛡️ 安全说明

- 厂商 API 密钥使用 `cryptography` 库加密存储，明文不落库
- 用户密码使用 `pbkdf2_sha256` 哈希，不可逆
- 厂商接口地址白名单机制，杜绝 SSRF 攻击
- 生产环境请务必：① 修改所有默认密码和密钥 ② 启用 HTTPS

---

## 🗺️ Roadmap

- [ ] 按 token 计费（当前按次计费）
- [ ] 更多厂商支持（Anthropic、Google 等）
- [ ] 用户注册功能
- [ ] 积分充值 / 提现流程
- [ ] 流式响应支持（SSE）
- [ ] 速率限制优化
- [ ] 多节点部署支持

---

## 🤝 贡献

欢迎提 Issue 和 PR！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交改动：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

---

## 📄 License

MIT License — 自由使用、修改和分发。

---

<div align="center">
  <sub>如果这个项目对你有帮助，欢迎点一个 ⭐</sub>
</div>
