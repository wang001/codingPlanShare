from cryptography.fernet import Fernet
import base64
from app.config.settings import settings

# 使用配置文件中的密钥
# 注意：在生产环境中，应该使用环境变量或安全的密钥管理方式
encryption_key = settings.security.get('encryption_key', 'your-encryption-key-123456789012345678901234')
# 确保密钥是32字节的url-safe base64编码
if len(encryption_key) < 32:
    # 补全密钥长度
    encryption_key = encryption_key.ljust(32, '0')
elif len(encryption_key) > 32:
    # 截断密钥长度
    encryption_key = encryption_key[:32]

# 转换为base64编码
ENCRYPTION_KEY = base64.urlsafe_b64encode(encryption_key.encode())
fernet = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """加密数据"""
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """解密数据"""
    return fernet.decrypt(encrypted_data.encode()).decode()