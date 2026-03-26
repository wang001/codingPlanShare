#!/usr/bin/env python3
"""
init_config.py — 初始化 config.yaml

功能：
1. 检测运行环境（SQLite / MySQL），按需生成对应配置
2. 检查必要环境变量是否已设置（MySQL 模式下）
3. 若 config.yaml 已存在则询问是否覆盖（可通过 --force 跳过询问）

用法：
  # 生成 MySQL 版本（默认）
  python3 init_config.py

  # 生成 SQLite 版本（本地开发）
  python3 init_config.py --sqlite

  # 强制覆盖已有配置（不询问）
  python3 init_config.py --force

  # SQLite + 强制覆盖
  python3 init_config.py --sqlite --force
"""

import argparse
import os
import sys

# 项目根目录（scripts/init/ 上两级）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")

# ── 配置模板 ──────────────────────────────────────────────────────────────

MYSQL_CONFIG_TEMPLATE = """\
# ==============================================================================
# config.yaml — CodingPlanShare 服务配置
# ==============================================================================
# 敏感字段通过环境变量注入，格式 ${ENV_VAR_NAME}
# 本地开发可在项目根目录创建 .env 文件（不要提交到 git）
# ==============================================================================

# 管理员配置
admin:
  password: "${ADMIN_PASSWORD}"   # 管理员初始密码，首次部署后务必修改

# 数据库配置（MySQL）
database:
  driver: "mysql"
  host: "${DB_HOST}"              # MySQL 地址，例如 127.0.0.1 或 RDS 域名
  port: 3306
  user: "${DB_USER}"              # 数据库用户名
  password: "${DB_PASSWORD}"      # 数据库密码，勿硬编码
  name: "coding_plan_share"       # 数据库名，需提前手动创建
  pool_size: 20                   # 连接池大小
  max_overflow: 40                # 超出 pool_size 时允许额外创建的连接数
  pool_recycle: 1800              # 连接最大存活时间（秒），防止 MySQL 8h 超时断连

# 限流配置
rate_limit:
  user_rpm: 60            # 单个用户每分钟最大请求数
  default_provider_rpm: 30  # 厂商密钥默认每分钟最大请求数

# 安全配置
security:
  encryption_key: "${ENCRYPTION_KEY}"   # API Key 加密密钥（32 字节随机字符串）
  jwt_secret: "${JWT_SECRET}"           # JWT 签名密钥（随机字符串，越长越安全）

# 超时配置
timeout:
  request_timeout: 5    # 上游 AI 接口请求超时（秒）

# 密钥管理配置
key_management:
  max_retry: 1            # 密钥失败后最大重试次数
  cool_down_period: 7200  # 密钥超限冷却时间（秒）
  max_concurrency: 1      # 每个密钥的最大并发数

# 日志配置
logging:
  level: "INFO"           # DEBUG / INFO / WARNING / ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

SQLITE_CONFIG_TEMPLATE = """\
# ==============================================================================
# config.yaml — CodingPlanShare 服务配置（SQLite 本地开发版）
# ==============================================================================

# 管理员配置
admin:
  password: "admin123"   # 管理员初始密码，本地开发用，生产环境务必修改

# 数据库配置（SQLite）
database:
  driver: "sqlite"
  path: "./data/coding_plan_share.db"   # SQLite 文件路径（相对于项目根目录）

# 限流配置
rate_limit:
  user_rpm: 60
  default_provider_rpm: 30

# 安全配置
security:
  encryption_key: "local-dev-encryption-key-change-me"   # 本地开发用，生产环境必须替换
  jwt_secret: "local-dev-jwt-secret-change-me"           # 本地开发用，生产环境必须替换

# 超时配置
timeout:
  request_timeout: 5

# 密钥管理配置
key_management:
  max_retry: 1
  cool_down_period: 7200
  max_concurrency: 1

# 日志配置
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

# ── 必要环境变量检查（MySQL 模式） ────────────────────────────────────────

REQUIRED_ENV_MYSQL = [
    ("DB_HOST",        "MySQL 数据库地址，例如 127.0.0.1"),
    ("DB_USER",        "数据库用户名"),
    ("DB_PASSWORD",    "数据库密码"),
    ("ENCRYPTION_KEY", "API Key 加密密钥（建议 32 字节随机字符串）"),
    ("JWT_SECRET",     "JWT 签名密钥（随机字符串）"),
    ("ADMIN_PASSWORD", "管理员初始密码"),
]


def check_env_vars():
    """检查 MySQL 模式所需的环境变量，打印缺失项"""
    missing = []
    for var, desc in REQUIRED_ENV_MYSQL:
        val = os.environ.get(var)
        if not val or val.startswith("${"):
            missing.append((var, desc))

    if missing:
        print("⚠️  以下环境变量尚未设置（MySQL 模式必须配置）：")
        for var, desc in missing:
            print(f"   {var:<20s} — {desc}")
        print()
        print("提示：可在项目根目录创建 .env 文件（不要提交到 git），格式：")
        print("   DB_HOST=127.0.0.1")
        print("   DB_USER=root")
        print("   ...")
        print()
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="初始化 config.yaml")
    parser.add_argument("--sqlite", action="store_true", help="生成 SQLite 版本（本地开发）")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有 config.yaml")
    args = parser.parse_args()

    # 检查是否已存在
    if os.path.exists(CONFIG_PATH) and not args.force:
        print(f"⚠️  config.yaml 已存在：{CONFIG_PATH}")
        ans = input("是否覆盖？[y/N] ").strip().lower()
        if ans != "y":
            print("取消，未做任何修改。")
            sys.exit(0)

    if args.sqlite:
        template = SQLITE_CONFIG_TEMPLATE
        db_mode = "SQLite（本地开发）"
    else:
        template = MYSQL_CONFIG_TEMPLATE
        db_mode = "MySQL（生产）"
        # 检查环境变量（仅提示，不阻止生成）
        ok = check_env_vars()
        if not ok:
            print("ℹ️  config.yaml 将包含 ${ENV_VAR} 占位符，请在启动前设置好环境变量。\n")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ config.yaml 已生成（{db_mode}）：{CONFIG_PATH}")

    if not args.sqlite:
        print()
        print("后续步骤：")
        print("  1. 确保 MySQL 数据库 'coding_plan_share' 已创建")
        print("  2. 执行建表 SQL：mysql -u <user> -p coding_plan_share < scripts/init/init_mysql.sql")
        print("  3. 设置好所有必要的环境变量（或 .env 文件）")
        print("  4. 启动服务：uvicorn app.main:app --reload")
    else:
        print()
        print("后续步骤：")
        print("  1. 执行 SQLite 初始化：python3 scripts/init/init_db.py")
        print("  2. 启动服务：uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
