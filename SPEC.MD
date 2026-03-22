# 后端实现规范文档

## 1. 项目结构

```
codingPlanShare/
├── app/
│   ├── api/            # API接口层
│   ├── services/       # 业务逻辑层
│   ├── models/         # 数据模型层
│   ├── schemas/        # 数据验证层
│   ├── utils/          # 工具函数
│   ├── db/             # 数据库连接
│   ├── config/         # 配置管理
│   └── main.py         # 应用入口
├── tests/              # 测试代码
├── data/               # 数据库文件
├── config.yaml         # 配置文件
├── requirements.txt    # 依赖管理
└── init_db.py          # 数据库初始化
```

## 2. 核心功能实现

### 2.1 数据库设计

- **用户表** (`users`): 存储用户信息，包含id、username、email、password_hash、balance、status等字段
- **密钥表** (`api_keys`): 存储API密钥信息，包含id、user_id、key_type、provider、encrypted_key等字段
- **积分明细表** (`point_logs`): 记录积分变动，包含id、user_id、amount、type、related_key_id等字段
- **调用日志表** (`call_logs`): 记录API调用日志，包含id、user_id、provider_key_id、model、status等字段
- **系统配置表** (`system_config`): 存储系统配置，包含key、value字段

### 2.2 内存缓存实现

- **MemoryCache类**: 实现了内存缓存功能，支持设置、获取、删除缓存
- **分段锁机制**: 使用16个分段锁，提高并发性能
- **缓存键设计**: `user:balance:{user_id}` 用于缓存用户积分余额
- **过期机制**: 支持设置缓存过期时间

### 2.3 后台任务系统

- **BackgroundTasks类**: 实现了后台任务功能
- **同步频率**: 每1秒执行一次缓存同步
- **同步内容**: 将缓存中的用户余额同步到数据库
- **异常处理**: 捕获并记录后台任务执行过程中的异常

### 2.4 积分服务

- **PointsService类**: 实现了积分管理功能
- **预扣积分**: 先从缓存获取余额，检查是否足够，然后更新缓存
- **确认扣费**: 记录积分变动日志
- **回滚积分**: 恢复缓存中的积分余额
- **增加积分**: 更新缓存并记录日志

### 2.5 认证服务

- **AuthService类**: 实现了用户认证功能
- **JWT生成**: 使用python-jose生成JWT令牌
- **密码验证**: 使用passlib进行密码哈希和验证
- **API密钥验证**: 验证API密钥的有效性

### 2.6 密钥管理服务

- **KeyService类**: 实现了密钥管理功能
- **密钥生成**: 生成平台API密钥
- **密钥加密**: 使用Fernet加密存储厂商API密钥
- **密钥状态管理**: 管理密钥的启用、禁用、超限和无效状态

### 2.7 路由服务

- **RouterService类**: 实现了请求路由功能
- **厂商选择**: 根据模型参数选择合适的厂商
- **密钥选择**: 使用轮询策略选择可用密钥
- **自动重试**: 密钥失效时自动重试其他可用密钥

### 2.8 API接口

- **认证接口**: `/api/v1/auth/login` 用于用户登录
- **用户接口**: `/api/v1/users/me` 用于获取个人信息
- **密钥接口**: `/api/v1/keys` 用于密钥管理
- **积分接口**: `/api/v1/points` 用于积分查询
- **聊天接口**: `/api/v1/chat/completions` 用于聊天完成
- **嵌入接口**: `/api/v1/embeddings` 用于文本嵌入
- **管理员接口**: `/admin/*` 用于后台管理

## 3. 技术实现细节

### 3.1 内存缓存与数据库同步

```python
# 内存缓存实现
class MemoryCache:
    def __init__(self):
        self._cache = {}
        self._expire_times = {}
        self._lock = threading.RLock()
        self._segment_locks = {}  # 分段锁字典
        self._num_segments = 16  # 分段数量

# 后台任务同步
async def _sync_user_balances(self, db: Session):
    user_balances = {}
    for key in cache.get_all_keys():
        if key.startswith("user:balance:"):
            user_id = int(key.split(":")[-1])
            user_balances[user_id] = cache.get(key)
    
    for user_id, balance in user_balances.items():
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.balance != balance:
                user.balance = balance
                db.commit()
        except Exception as e:
            print(f"同步用户 {user_id} 积分失败: {e}")
            db.rollback()
```

### 3.2 积分操作流程

```python
# 预扣积分
def pre_deduct_points(db: Session, user_id: int, amount: int) -> bool:
    # 先从缓存获取当前余额
    current_balance = PointsService.get_user_balance(db, user_id)
    if current_balance < amount:
        return False
    
    # 更新缓存
    new_balance = current_balance - amount
    cache_key = f"user:balance:{user_id}"
    cache.set(cache_key, new_balance, expire_seconds=3600)
    return True

# 增加积分
def add_points(db: Session, user_id: int, amount: int, log_type: int, ...):
    # 从缓存获取当前余额
    current_balance = PointsService.get_user_balance(db, user_id)
    
    # 更新缓存
    new_balance = current_balance + amount
    cache_key = f"user:balance:{user_id}"
    cache.set(cache_key, new_balance, expire_seconds=3600)
    
    # 记录积分变动日志
    point_log = PointLog(
        user_id=user_id,
        amount=amount,
        type=log_type,
        ...
    )
    db.add(point_log)
    db.commit()
```

### 3.3 并发安全处理

- **分段锁**: 使用16个分段锁，根据key的哈希值分配到不同的分段
- **原子操作**: 每个缓存操作都是原子的，避免并发竞争
- **线程安全**: 所有缓存操作都使用锁保护，确保线程安全

### 3.4 流式响应支持

- **SSE实现**: 支持Server-Sent Events流式响应
- **异步处理**: 使用FastAPI的异步特性处理流式请求
- **厂商适配**: 适配不同厂商的流式API

## 4. 配置管理

### 4.1 配置文件

```yaml
# config.yaml
admin:
  password: "admin123"
database:
  driver: "sqlite"
  path: "./data/app.db"
security:
  encryption_key: "your-encryption-key"
  jwt_secret: "your-jwt-secret"
```

### 4.2 环境变量

- **加密密钥**: 通过配置文件设置，用于加密厂商API密钥
- **JWT密钥**: 通过配置文件设置，用于生成JWT令牌
- **数据库路径**: 通过配置文件设置，指定SQLite数据库文件路径

## 5. 测试策略

### 5.1 单元测试

- **缓存测试**: 测试内存缓存的并发安全性
- **积分测试**: 测试积分操作的正确性
- **认证测试**: 测试认证服务的功能
- **密钥测试**: 测试密钥管理的功能

### 5.2 集成测试

- **完整流程测试**: 测试从请求接收到响应返回的完整流程
- **异常处理测试**: 测试各种异常情况下的处理逻辑
- **性能测试**: 测试系统在高并发下的性能

## 6. 部署方案

### 6.1 本地部署

1. 安装依赖: `pip install -r requirements.txt`
2. 初始化数据库: `python init_db.py`
3. 启动服务: `uvicorn app.main:app --host 0.0.0.0 --port 3000`

### 6.2 容器部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
```

## 7. 性能优化

1. **缓存优化**: 使用内存缓存减少数据库访问
2. **分段锁**: 提高并发性能
3. **异步处理**: 使用FastAPI的异步特性
4. **批量更新**: 积分更新采用批量异步更新
5. **连接池**: 使用数据库连接池

## 8. 安全措施

1. **密钥加密**: 厂商API密钥使用Fernet加密存储
2. **密码哈希**: 用户密码使用pbkdf2_sha256哈希存储
3. **JWT认证**: 使用JWT进行API认证
4. **输入验证**: 对所有用户输入进行严格验证
5. **日志审计**: 记录所有敏感操作的审计日志

## 9. 监控与维护

1. **日志监控**: 使用结构化日志，便于分析和排查问题
2. **健康检查**: 提供健康检查接口，监控系统状态
3. **定期备份**: 定期备份数据库，防止数据丢失
4. **性能监控**: 监控系统的响应时间和QPS

## 10. 实现进度

### 10.1 已完成功能

- **多厂商API适配**: 实现了ModelScope厂商的API调用
- **积分计费系统**: 实现了积分的预扣、确认和回滚
- **内存缓存**: 提高性能，减少数据库访问
- **后台同步**: 确保数据安全，防止数据丢失
- **并发安全**: 支持高并发请求
- **流式响应**: 支持流式API调用
- **API密钥管理**: 实现了API密钥的生成、验证和管理
- **用户认证**: 实现了基于JWT的用户认证
- **错误处理**: 实现了完善的错误处理机制
- **重试机制**: 实现了API调用失败时的自动重试

### 10.2 技术优化

- **缓存优化**: 优化了select_provider_key方法，使用缓存减少数据库查询
- **SQLAlchemy错误修复**: 解决了DetachedInstanceError问题
- **配置管理**: 实现了基于config.yaml的配置管理
- **日志记录**: 增加了详细的日志记录，便于调试

### 10.3 测试覆盖

- **聊天接口测试**: 测试了chat/completions接口的功能
- **流式响应测试**: 测试了流式聊天接口的功能
- **提供商测试**: 测试了ModelScope提供商的API调用
- **模型序列化测试**: 测试了模型对象的序列化功能

## 11. 总结

本后端实现基于FastAPI和SQLite，采用模块化设计，实现了一个轻量级的LLM API聚合计费路由器。核心功能包括：

- **多厂商API适配**: 支持多个LLM厂商的API调用
- **积分计费系统**: 实现了积分的预扣、确认和回滚
- **内存缓存**: 提高性能，减少数据库访问
- **后台同步**: 确保数据安全，防止数据丢失
- **并发安全**: 支持高并发请求
- **流式响应**: 支持流式API调用

通过本实现，可以为开发者提供统一的LLM API接口，降低模型调用成本，提高开发效率。