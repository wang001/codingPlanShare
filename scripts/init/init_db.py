from app.db.database import engine, Base, get_db
from app.models import User, ApiKey, PointLog, CallLog, SystemConfig
from app.services.auth_service import AuthService

# 创建所有表
Base.metadata.create_all(bind=engine)

# 创建默认用户
from sqlalchemy.orm import Session
db = next(get_db())

# 检查是否已存在用户
if db.query(User).count() == 0:
    # 创建默认管理员用户
    default_user = User(
        username="admin",
        email="admin@example.com",
        password_hash=AuthService.get_password_hash("admin123"),
        balance=1000,
        status=1
    )
    db.add(default_user)
    db.commit()
    print("默认用户创建成功：用户名=admin，密码=admin123")
else:
    print("用户已存在，跳过默认用户创建")

print("数据库初始化完成，表结构已创建")