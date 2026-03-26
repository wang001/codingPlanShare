<div align="center">

# 🔀 LLM Router

**轻量级 LLM API 聚合网关 · Lightweight LLM API Aggregation & Credit Billing Gateway**

把闲置的 API 额度变成收益，让所有人都能低成本用上好模型。  
Turn idle API quota into revenue. One unified OpenAI-compatible endpoint for every LLM vendor.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

[English](./README.en.md) · 中文

</div>

> **关键词 / Keywords**：LLM 网关 · API 聚合 · 积分计费 · 密钥池路由 · OpenAI 兼容 · 大模型代理  
> LLM gateway · API aggregation · credit billing · key pool routing · OpenAI compatible · LLM proxy · AI API hub

---

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
| **积分写入** | 进程内缓存 + 后台异步落库 | 直接写 DB，行锁保证原子性 |
| **进程状态** | 有状态（重启后从 DB 重新加载） | 无状态（任意实例可随时重启/扩容） |
| **依赖** | 仅 Python + SQLite，零外部依赖 | 需外部 MySQL 8.0+ |
| **切换成本** | 修改 `config.yaml` 中 `driver`，重启即可 | |

---

## ✨ 核心特性

- 🔌 **OpenAI 兼容接口** — 无需改动现有代码，只需替换 `base_url`
- 🏦 **双阶段积分计费** — 预扣 + 确认，失败自动回滚，不多扣一分
- 🔑 **密钥池路由** — 自动选择可用密钥，失效自动重试，对调用方透明
- 🛡️ **SSRF 防护** — 厂商 URL 白名单，只允许访问已知合法地址
- 📊 **管理后台** — 用户、密钥、积分、日志全套可视化
- 🌊 **流式响应** — 支持 SSE 流式输出（`/api/v1/chat/completions/stream`）

---

## 🏗️ 支持的厂商

| 厂商 | 模型示例 | 调用前缀 |
|------|---------|---------|
| ModelScope | moonshotai/Kimi-K2.5、Qwen 系列 | `modelscope/` |
| 智谱 AI | GLM-4 | `zhipu/` |
| MiniMax | abab6.5 | `minimax/` |
| 阿里云百炼 | qwen-turbo | `alibaba/` |
| 腾讯混元 | hunyuan-pro | `tencent/` |
| 百度千帆 | ernie-4.0 | `baidu/` |
| DeepSeek | deepseek-chat | `deepseek/` |
| SiliconFlow | 多种开源模型 | `siliconflow/` |

> **模型格式**：`provider/真实模型名`，例如 `model: "modelscope/moonshotai/Kimi-K2.5"`，第一段是 provider，后面是真实模型名。

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 16+

### 1. 克隆仓库

```bash
git clone https://github.com/wang001/codingPlanShare.git
cd codingPlanShare
```

### 2. 启动后端

```bash
# 安装依赖（国内用户推荐加镜像源）
pip install -r requirements.txt
# pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 初始化配置文件（首次部署）
# SQLite 本地开发模式（无需外部数据库）
python3 scripts/init/init_config.py --sqlite
# MySQL 生产模式（需提前设置环境变量，见配置说明）
# python3 scripts/init/init_config.py

# 初始化数据库
# SQLite：
python3 scripts/init/init_db.py
# MySQL：先手动创建数据库，再执行建表 SQL：
# mysql -u <user> -p coding_plan_share < scripts/init/init_mysql.sql

# 启动服务（默认端口 3000）
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

访问 http://localhost:3000/docs 查看自动生成的 API 文档。

### 3. 启动前端

```bash
cd frontend
npm install --include=dev
# 国内用户：npm install --include=dev --registry https://registry.npmmirror.com
npm run dev
```

访问 http://localhost:5173 打开管理界面。

### 4. 初始账号

| 角色 | 账号 |
|------|------|
| 普通用户 | 邮箱 `admin@example.com`，密码 `admin123` |
| 管理员 | 密码 `admin123`（切换到「管理员登录」Tab） |

> ⚠️ **首次部署后请立即修改 `config.yaml` 中的所有默认密码和密钥！**

### 5. 发起第一次调用

1. 以管理员登录，创建用户
2. 以用户登录，在「密钥」页面托管你的厂商 API 密钥
3. 创建一个平台调用密钥
4. 调用接口：

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

---

## ⚙️ 配置说明

编辑 `config.yaml`：

```yaml
# 管理员
admin:
  password: "your-strong-password"

# 安全（生产环境必须修改）
security:
  encryption_key: "${ENCRYPTION_KEY}"   # 厂商密钥加密主密钥（Fernet）
  jwt_secret: "${JWT_SECRET}"           # JWT 签名密钥

# 数据库 - SQLite 单机
database:
  driver: "sqlite"
  path: "./data/app.db"

# 数据库 - MySQL 无状态（多实例）
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

# 限流
rate_limit:
  user_rpm: 60
  default_provider_rpm: 30

# 超时（秒）
timeout:
  request_timeout: 30

# 密钥管理
key_management:
  max_retry: 1          # 厂商失败最大重试次数
  cool_down_period: 7200  # 超限冷却时间（秒）
```

> 敏感值（`ENCRYPTION_KEY`、`JWT_SECRET`、`DB_USER`、`DB_PASSWORD`）通过环境变量或 `.env` 文件注入，不要提交到 Git。

---

## 🐳 Docker 部署

```bash
docker build -t llm-router .

# SQLite 单机
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e ENCRYPTION_KEY=your-key \
  -e JWT_SECRET=your-secret \
  llm-router

# MySQL 无状态
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
│       ├── api/        # 接口请求封装
│       ├── layouts/    # 用户端/管理员端布局
│       └── pages/      # 页面组件
├── scripts/
│   └── init/
│       ├── init_config.py  # 生成 config.yaml（支持 SQLite/MySQL 模式）
│       ├── init_db.py      # 初始化 SQLite 数据库 & 默认用户
│       └── init_mysql.sql  # MySQL 建表脚本（幂等，可重复执行）
├── tests/              # 单元测试 & 回归测试
├── config.yaml         # 配置文件（由 init_config.py 生成）
└── requirements.txt
```

---

## 🔌 接口速览

> 完整文档：`http://localhost:3000/docs`

### 用户端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/users/me` | 当前用户信息 |
| GET/POST | `/api/v1/keys` | 密钥列表 / 创建 |
| PUT/DELETE | `/api/v1/keys/{id}` | 更新 / 删除密钥 |
| GET | `/api/v1/points` | 积分余额 |
| GET | `/api/v1/points/logs` | 积分明细 |
| POST | `/api/v1/chat/completions` | 对话接口（需 `api-key` header） |
| POST | `/api/v1/chat/completions/stream` | 流式对话 |
| POST | `/api/v1/embeddings` | 嵌入接口 |

### 管理员端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/admin/login` | 管理员登录 |
| GET/POST | `/api/admin/users` | 用户列表 / 创建 |
| PUT | `/api/admin/users/{id}` | 更新用户状态 |
| POST | `/api/admin/points` | 调整用户积分 |
| GET | `/api/admin/keys` | 所有密钥 |
| PUT/DELETE | `/api/admin/keys/{id}` | 管理密钥状态 |
| GET | `/api/admin/logs` | 调用日志 |

---

## 🛡️ 安全说明

- 厂商密钥使用 Fernet 加密落库，明文不入库
- 用户密码 `pbkdf2_sha256` 哈希，不可逆
- 厂商接口地址白名单，杜绝 SSRF
- 生产环境请修改所有默认值并启用 HTTPS

---

## 🗺️ Roadmap

- [ ] 按 token 计费（当前按次，固定 10 积分/次）
- [ ] 更多厂商支持（Anthropic、Google 等）
- [ ] 用户自助注册
- [ ] 积分充值 / 提现流程
- [x] 流式响应（SSE）✅
- [ ] 限流优化
- [ ] 多节点部署指南

---

## 🤝 贡献

欢迎提 Issue 和 PR！

```bash
git checkout -b feature/your-feature
git commit -m 'feat: add your feature'
git push origin feature/your-feature
# 提交 Pull Request
```

---

## 📄 License

MIT — 自由使用、修改和分发。

---

<div align="center">
  <sub>如果这个项目对你有帮助，欢迎点一个 ⭐</sub>
</div>
