<div align="center">

# 🔀 LLM Router

**A lightweight LLM API aggregation & credit billing gateway**

Turn your idle API quota into revenue. Let everyone access great models at low cost.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

English · [中文](./README.md)

</div>

---

## 💡 What is this?

Many developers have idle LLM API quotas — subscriptions they bought but barely use, or company allocations left over. At the same time, other developers need to call various models but don't want to integrate with a dozen different vendor APIs.

**LLM Router** bridges these two groups:

- **Key hosters**: Host your vendor API keys on the platform and earn credits every time they are used
- **API callers**: Use a single OpenAI-compatible endpoint and spend credits to call models from multiple vendors
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

## ✨ Features

- 🔌 **OpenAI-compatible API** — Drop-in replacement: just change `base_url`, no code changes needed
- 🏦 **Two-phase billing** — Pre-deduct → confirm on success, auto-rollback on failure, never over-charge
- 🔑 **Key pool routing** — Auto-selects available vendor keys, retries on failure, transparent to callers
- 🛡️ **SSRF protection** — Vendor URL allowlist, only known legitimate vendor addresses permitted
- 📊 **Admin dashboard** — User management, key management, credit adjustment, call logs
- 🌊 **Streaming support** — SSE streaming via `/api/v1/chat/completions/stream`

---

## 🏗️ Supported Vendors

| Provider | Example Models | Prefix |
|----------|---------------|--------|
| ModelScope | moonshotai/Kimi-K2.5, Qwen series | `modelscope/` |
| Zhipu AI | GLM-4 | `zhipu/` |
| MiniMax | abab6.5 | `minimax/` |
| Alibaba Bailian | qwen-turbo | `alibaba/` |
| Tencent Hunyuan | hunyuan-pro | `tencent/` |
| Baidu Qianfan | ernie-4.0 | `baidu/` |
| DeepSeek | deepseek-chat | `deepseek/` |
| SiliconFlow | Various open-source models | `siliconflow/` |

> **Model format**: `provider/actual-model-name`  
> Example: `model: "modelscope/moonshotai/Kimi-K2.5"` — first segment is the provider, the rest is the real model name.

---

## 🚀 Quick Start

### Requirements

- Python 3.11+
- Node.js 16+

### 1. Clone

```bash
git clone https://github.com/wang001/codingPlanShare.git
cd codingPlanShare
```

### 2. Start Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start server (default port 3000)
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Visit http://localhost:3000/docs for the auto-generated API docs.

### 3. Start Frontend

```bash
cd frontend
npm install --include=dev
npm run dev
```

Visit http://localhost:5173 for the admin UI.

### 4. Default Credentials

| Role | Credentials |
|------|-------------|
| Regular user | Email: `admin@example.com` · Password: `admin123` |
| Admin | Password: `admin123` (switch to "Admin Login" tab) |

> ⚠️ **Change all default passwords and keys in `config.yaml` immediately after first deploy!**

### 5. Make Your First Call

1. Log in as admin and create a user
2. Log in as user, go to the "Keys" page and host a vendor API key
3. Create a platform call key
4. Call the API:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-platform-key",
    base_url="http://localhost:3000/api/v1/chat",
)

response = client.chat.completions.create(
    model="modelscope/moonshotai/Kimi-K2.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

> The SDK sends `Authorization: Bearer <key>`, which the gateway also accepts.

---

## ⚙️ Configuration

Edit `config.yaml`:

```yaml
# Admin
admin:
  password: "your-strong-password"

# Security (must change in production)
security:
  encryption_key: "${ENCRYPTION_KEY}"   # Fernet key for vendor key encryption
  jwt_secret: "${JWT_SECRET}"           # JWT signing key

# Database - SQLite (single node)
database:
  driver: "sqlite"
  path: "./data/app.db"

# Database - MySQL (stateless multi-instance)
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

# Rate limiting
rate_limit:
  user_rpm: 60
  default_provider_rpm: 30

# Timeout (seconds)
timeout:
  request_timeout: 30

# Key management
key_management:
  max_retry: 1            # Max retry attempts on vendor failure
  cool_down_period: 7200  # Cooldown after rate-limit hit (seconds)
```

> Sensitive values (`ENCRYPTION_KEY`, `JWT_SECRET`, `DB_USER`, `DB_PASSWORD`) should be set via environment variables or a `.env` file — never committed to Git.

---

## 🐳 Docker

```bash
docker build -t llm-router .

# SQLite (single node)
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -e ENCRYPTION_KEY=your-key \
  -e JWT_SECRET=your-secret \
  llm-router

# MySQL (stateless)
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

## 📁 Project Structure

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

## 🔌 API Reference

> Full interactive docs at: `http://localhost:3000/docs`

### User API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/users/me` | Current user info |
| GET/POST | `/api/v1/keys` | List / create keys |
| PUT/DELETE | `/api/v1/keys/{id}` | Update / delete key |
| GET | `/api/v1/points` | Credit balance |
| GET | `/api/v1/points/logs` | Credit history |
| POST | `/api/v1/chat/completions` | Chat completion (needs `api-key` header) |
| POST | `/api/v1/chat/completions/stream` | Streaming chat |
| POST | `/api/v1/embeddings` | Embeddings |

### Admin API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/admin/login` | Admin login |
| GET/POST | `/api/admin/users` | List / create users |
| PUT | `/api/admin/users/{id}` | Update user status |
| POST | `/api/admin/points` | Adjust user credits |
| GET | `/api/admin/keys` | All keys |
| PUT/DELETE | `/api/admin/keys/{id}` | Manage key status |
| GET | `/api/admin/logs` | Call logs |

---

## 🛡️ Security

- Vendor API keys encrypted at rest via `cryptography` (Fernet) — no plaintext in DB
- User passwords hashed with `pbkdf2_sha256`, non-reversible
- Vendor URL allowlist prevents SSRF attacks
- In production: change all defaults and enable HTTPS

---

## 🗺️ Roadmap

- [ ] Token-based billing (current: flat 10 credits/call)
- [ ] More vendors: Anthropic, Google, etc.
- [ ] User self-registration
- [ ] Credit top-up / withdrawal flow
- [x] Streaming SSE responses ✅
- [ ] Rate limiting improvements
- [ ] Multi-node deployment guide

---

## 🤝 Contributing

PRs and Issues welcome!

```bash
git checkout -b feature/your-feature
git commit -m 'feat: add your feature'
git push origin feature/your-feature
# Open a Pull Request
```

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">
  <sub>If this project helps you, please give it a ⭐</sub>
</div>
