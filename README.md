<div align="center">

# 🔀 LLM Router

**A lightweight LLM API aggregation & credit billing gateway**

**一个轻量级的 LLM API 聚合计费网关**

Turn your idle API quota into revenue. Let everyone access great models at low cost.

把你手里闲置的 API 额度变成收益，让大家都能低成本用上好模型。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

[English](#-what-is-this) · [中文](#-这是什么)

</div>

---

## 💡 What is this?

Many developers have idle LLM API quotas — subscriptions they bought but barely use, or company allocations left over. At the same time, other developers need to call various models but don't want to integrate with a dozen different vendor APIs.

**LLM Router** bridges these two groups:

- **Key hosters**:托管你的厂商密钥到平台，每次被调用时自动获得积分收益
- **API callers**: Use a single OpenAI-compatible endpoint, spend credits to call models from multiple vendors
- **Platform**: Takes a small margin to sustain operations

The system is fully open source. You can self-host it for your team or run it as a public service.

### Two Deployment Modes

| | SQLite Mode | MySQL Mode |
|--|-------------|------------|
| **Use case** | Local dev, single-node operation | Production, multi-instance horizontal scaling |
| **Credit writes** | In-process cache + async delta flush | Direct DB write with row-level locks |
| **Process state** | Stateful (reloads from DB on restart) | Stateless (any instance can restart freely) |
| **Dependencies** | Python + SQLite only, zero external deps | Requires MySQL 8.0+ |
| **Switch cost** | Change `driver` in `config.yaml`, restart | |

---

## 💡 这是什么？

很多开发者手里都有闲置的 LLM 厂商 API 额度——充了会员用不完、公司采购了没怎么用。与此同时，另一批开发者需要调用各种模型，但不想对接十几家厂商的不同接口。

**LLM Router** 就是连接这两类人的桥梁：

- **托管者**：把你的厂商密钥托管到平台，每次被调用时自动获得积分收益
- **调用者**：用一个统一的 OpenAI 兼容接口，消耗积分调用多家厂商的模型
- **平台**：从中抽取少量差价维持运营

整个系统完全开源，你可以自己搭一个给团队用，也可以对外运营。

### 两种部署模式

| | SQLite 单机模式 | MySQL 无状态模式 |
|--|----------------|----------------|
| **定位** | 本地开发、单机运营 | 生产环境、多实例水平扩展 |
| **积分写入** | 进程内缓存 + 后台异步 delta flush | 直接写 DB，行锁保证原子性 |
| **进程状态** | 有状态（重启后从 DB 重新加载） | 无状态（任意实例可随时重启/扩容） |
| **依赖** | 仅 Python + SQLite，零外部依赖 | 需外部 MySQL 8.0+ |
| **切换成本** | 修改 `config.yaml` 中 `driver`，重启即可 | |

---

## ✨ Features / 核心特性

- 🔌 **OpenAI-compatible API** — Drop-in replacement: just change `base_url`, no code changes needed  
  **OpenAI 兼容接口** — 无需改动现有代码，只需替换 `base_url`
- 🏦 **Two-phase billing** — Pre-deduct → confirm on success, auto-rollback on failure, never over-charge  
  **双阶段积分计费** — 预扣 + 确认，失败自动回滚，不多扣一分
- 🔑 **Key pool routing** — Auto-selects available vendor keys, retries on failure, transparent to callers  
  **密钥池路由** — 自动选择可用密钥，失效自动重试，对调用方透明
- 🛡️ **SSRF protection** — Vendor URL allowlist, only known legitimate vendor addresses permitted  
  **SSRF 防护** — 厂商 URL 白名单，只允许访问已知合法地址
- 📊 **Admin dashboard** — User management, key management, credit adjustment, call logs  
  **管理后台** — 用户、密钥、积分、日志全套可视化
- 🌊 **Streaming support** — SSE streaming responses via `/api/v1/chat/completions/stream`  
  **流式响应** — 支持 SSE 流式输出

---

## 🏗️ Supported Vendors / 支持的厂商

| Provider | Example Models | Prefix |
|----------|---------------|--------|
| ModelScope | moonshotai/Kimi-K2.5, Qwen series | `modelscope/` |
| Zhipu AI / 智谱 | GLM-4 | `zhipu/` |
| MiniMax | abab6.5 | `minimax/` |
| Alibaba Bailian / 阿里百炼 | qwen-turbo | `alibaba/` |
| Tencent Hunyuan / 腾讯混元 | hunyuan-pro | `tencent/` |
| Baidu Qianfan / 百度千帆 | ernie-4.0 | `baidu/` |
| DeepSeek | deepseek-chat | `deepseek/` |
| SiliconFlow | Various open-source models | `siliconflow/` |

> **Model format / 模型格式**: `provider/actual-model-name`  
> Example: `model: "modelscope/moonshotai/Kimi-K2.5"` — first segment is the provider, the rest is the real model name.

---

## 🚀 Quick Start / 快速开始

### Requirements / 环境要求

- Python 3.11+
- Node.js 16+

### 1. Clone / 克隆仓库

```bash
git clone https://github.com/wang001/codingPlanShare.git
cd codingPlanShare
```

### 2. Start Backend / 启动后端

```bash
# Install dependencies
# 安装依赖（国内用户推荐加镜像源）
pip install -r requirements.txt
# pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Initialize database / 初始化数据库
python init_db.py

# Start server (default port 3000) / 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Visit / 访问 http://localhost:3000/docs for the auto-generated API docs.

### 3. Start Frontend / 启动前端

```bash
cd frontend

# Install dependencies / 安装依赖
npm install --include=dev
# 国内用户：npm install --include=dev --registry https://registry.npmmirror.com

# Dev mode / 开发模式
npm run dev
```

Visit / 访问 http://localhost:5173 for the admin UI.

### 4. Default Credentials / 初始账号

| Role / 角色 | Credentials / 账号 |
|-------------|-------------------|
| Regular user / 普通用户 | Email: `admin@example.com` · Password: `admin123` |
| Admin / 管理员 | Password: `admin123`（switch to "Admin Login" tab / 切换到「管理员登录」Tab） |

> ⚠️ **Change all default passwords and keys in `config.yaml` immediately after first deploy!**  
> ⚠️ **首次部署后请立即修改 `config.yaml` 中的所有默认密码和密钥！**

### 5. Make Your First Call / 发起第一次调用

1. Log in as admin, create a user / 以管理员登录，创建用户
2. Log in as user, host a vendor API key on the "Keys" page / 以用户登录，在「密钥」页面托管厂商密钥
3. Create a platform call key / 创建平台调用密钥
4. Call the API / 调用接口：

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-platform-key",   # 你的平台密钥
    base_url="http://localhost:3000/api/v1/chat",
)

response = client.chat.completions.create(
    model="modelscope/moonshotai/Kimi-K2.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

> The SDK sends `Authorization: Bearer <key>` which the gateway also accepts.  
> SDK 发送 `Authorization: Bearer <key>`，网关同样支持此格式。

---

## ⚙️ Configuration / 配置说明

Edit `config.yaml` / 编辑 `config.yaml`：

```yaml
# Admin / 管理员
admin:
  password: "your-strong-password"

# Security (must change in production) / 安全（生产环境必须修改）
security:
  encryption_key: "${ENCRYPTION_KEY}"   # Fernet key for vendor key encryption / 厂商密钥加密主密钥
  jwt_secret: "${JWT_SECRET}"           # JWT signing key / JWT 签名密钥

# Database / 数据库
database:
  driver: "sqlite"          # "sqlite" for single-node / "mysql" for stateless multi-instance
  path: "./data/app.db"     # SQLite only / 仅 SQLite 模式使用

# MySQL (when driver: "mysql")
# database:
#   driver: "mysql"
#   host: "your-mysql-host"
#   port: 3306
#   user: "${DB_USER}"
#   password: "${DB_PASSWORD}"
#   name: "llm_router"
#   pool_size: 20
#   max_overflow: 40
#   pool_recycle: 1800

# Rate limiting / 限流
rate_limit:
  user_rpm: 60
  default_provider_rpm: 30

# Timeout / 超时
timeout:
  request_timeout: 30       # seconds / 秒

# Key management / 密钥管理
key_management:
  max_retry: 1              # max retry attempts on vendor failure / 厂商失败最大重试次数
  cool_down_period: 7200    # cooldown after rate-limit (seconds) / 超限冷却时间（秒）
```

Sensitive values (`ENCRYPTION_KEY`, `JWT_SECRET`, `DB_USER`, `DB_PASSWORD`) should be set via environment variables or a `.env` file — never committed to Git.

敏感值（`ENCRYPTION_KEY`、`JWT_SECRET`、`DB_USER`、`DB_PASSWORD`）应通过环境变量或 `.env` 文件注入，不要提交到 Git。

---

## 🐳 Docker / Docker 部署

```bash
docker build -t llm-router .

# SQLite (single node) / SQLite 单机
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e ENCRYPTION_KEY=your-key \
  -e JWT_SECRET=your-secret \
  llm-router

# MySQL (stateless) / MySQL 无状态
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e ENCRYPTION_KEY=your-key \
  -e JWT_SECRET=your-secret \
  -e DB_USER=your-db-user \
  -e DB_PASSWORD=your-db-password \
  llm-router
```

---

## 📁 Project Structure / 项目结构

```
codingPlanShare/
├── app/
│   ├── api/            # HTTP routes (auth/users/keys/points/chat/admin)
│   ├── services/       # Business logic (auth/points/keys/router/admin)
│   ├── providers/      # Vendor adapters (unified OpenAI-compatible format)
│   ├── models/         # ORM models
│   ├── schemas/        # Request/response schemas
│   ├── utils/          # Helpers (encryption/cache/background tasks)
│   └── main.py         # App entrypoint
├── frontend/
│   └── src/
│       ├── api/        # Axios request layer
│       ├── layouts/    # User / admin layouts
│       └── pages/      # Page components
├── tests/              # Unit & regression tests
├── config.yaml         # Configuration file
├── init_db.py          # DB initializer
└── requirements.txt
```

---

## 🔌 API Reference / 接口速览

> Full docs at / 完整文档见：`http://localhost:3000/docs`

### User API / 用户端接口

| Method | Path | Description / 说明 |
|--------|------|--------------------|
| POST | `/api/v1/auth/login` | Login / 用户登录 |
| GET | `/api/v1/users/me` | Current user info / 当前用户信息 |
| GET/POST | `/api/v1/keys` | List / create keys / 密钥列表 / 创建 |
| PUT/DELETE | `/api/v1/keys/{id}` | Update / delete key / 更新 / 删除密钥 |
| GET | `/api/v1/points` | Credit balance / 积分余额 |
| GET | `/api/v1/points/logs` | Credit history / 积分明细 |
| POST | `/api/v1/chat/completions` | Chat completion (needs `api-key` header) / 对话接口 |
| POST | `/api/v1/chat/completions/stream` | Streaming chat / 流式对话 |
| POST | `/api/v1/embeddings` | Embeddings / 嵌入接口 |

### Admin API / 管理员接口

| Method | Path | Description / 说明 |
|--------|------|--------------------|
| POST | `/api/v1/auth/admin/login` | Admin login / 管理员登录 |
| GET/POST | `/api/admin/users` | List / create users / 用户列表 / 创建 |
| PUT | `/api/admin/users/{id}` | Update user status / 更新用户状态 |
| POST | `/api/admin/points` | Adjust user credits / 调整用户积分 |
| GET | `/api/admin/keys` | All keys / 所有密钥 |
| PUT/DELETE | `/api/admin/keys/{id}` | Manage key status / 管理密钥状态 |
| GET | `/api/admin/logs` | Call logs / 调用日志 |

---

## 🛡️ Security / 安全说明

- Vendor API keys encrypted at rest via `cryptography` (Fernet) — no plaintext in DB  
  厂商密钥使用 Fernet 加密落库，明文不入库
- User passwords hashed with `pbkdf2_sha256`, non-reversible  
  用户密码 pbkdf2_sha256 哈希，不可逆
- Vendor URL allowlist prevents SSRF attacks  
  厂商接口地址白名单，杜绝 SSRF
- In production: change all defaults and enable HTTPS  
  生产环境请修改所有默认值并启用 HTTPS

---

## 🗺️ Roadmap

- [ ] Token-based billing (current: flat 10 credits/call) / 按 token 计费（当前按次）
- [ ] More vendors: Anthropic, Google, etc. / 更多厂商支持
- [ ] User self-registration / 用户自助注册
- [ ] Credit top-up / withdrawal flow / 积分充值 / 提现
- [x] Streaming SSE responses / 流式响应 ✅
- [ ] Rate limiting improvements / 限流优化
- [ ] Multi-node deployment guide / 多节点部署指南

---

## 🤝 Contributing / 贡献

PRs and Issues welcome! / 欢迎提 Issue 和 PR！

```bash
git checkout -b feature/your-feature
git commit -m 'feat: add your feature'
git push origin feature/your-feature
# Open a Pull Request
```

---

## 📄 License

MIT — free to use, modify, and distribute. / 自由使用、修改和分发。

---

<div align="center">
  <sub>If this project helps you, please give it a ⭐ / 如果对你有帮助，欢迎点一个 ⭐</sub>
</div>
