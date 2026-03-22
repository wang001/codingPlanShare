import yaml
import os

class Settings:
    def __init__(self):
        # 加载配置文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 管理员配置
        self.admin = self.config.get('admin', {})
        
        # 数据库配置
        self.database = self.config.get('database', {})
        
        # 限流配置
        self.rate_limit = self.config.get('rate_limit', {})
        
        # 加密配置
        self.security = self.config.get('security', {})
        
        # 超时配置
        self.timeout = self.config.get('timeout', {})
        
        # 密钥管理配置
        self.key_management = self.config.get('key_management', {})
        
        # 缓存配置
        self.cache = self.config.get('cache', {})
        
        # 日志配置
        self.logging = self.config.get('logging', {})

# 创建全局配置实例
settings = Settings()