import os
import re
import yaml


def _load_dotenv():
    """启动时加载项目根目录的 .env 文件（如果存在），不覆盖已有环境变量。"""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '.env'
    )
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:   # 不覆盖已有环境变量
                os.environ[key] = val


_load_dotenv()


def _expand_env(value):
    """
    递归展开配置值中的环境变量占位符。
    格式：${ENV_VAR_NAME}
    找不到对应环境变量时保留原始占位符（不静默失败，方便排查）。
    """
    if isinstance(value, str):
        def replacer(m):
            var = m.group(1)
            env_val = os.environ.get(var)
            if env_val is None:
                # 未设置时保留占位符，启动时会在用到的地方报错
                return m.group(0)
            return env_val
        return re.sub(r'\$\{([^}]+)\}', replacer, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(i) for i in value]
    return value


class Settings:
    def __init__(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config.yaml'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f)

        # 展开所有 ${ENV_VAR} 占位符
        self.config = _expand_env(raw)

        self.admin        = self.config.get('admin', {})
        self.database     = self.config.get('database', {})
        self.rate_limit   = self.config.get('rate_limit', {})
        self.security     = self.config.get('security', {})
        self.timeout      = self.config.get('timeout', {})
        self.key_management = self.config.get('key_management', {})
        self.cache        = self.config.get('cache', {})
        self.logging      = self.config.get('logging', {})


settings = Settings()
