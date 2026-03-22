from fastapi import FastAPI
from app.api import auth, users, keys, points, chat, embeddings, admin
from app.utils.background_tasks import background_tasks

app = FastAPI(
    title="LLM API聚合计费路由器",
    description="一个轻量级的LLM API聚合计费路由器，支持多厂商API适配、积分计费、密钥管理等功能",
    version="1.0.0"
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["密钥"])
app.include_router(points.router, prefix="/api/v1/points", tags=["积分"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["聊天"])
app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["嵌入"])
app.include_router(admin.router, prefix="/admin", tags=["管理员"])

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    await background_tasks.start()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    await background_tasks.stop()

@app.get("/")
def read_root():
    """根路径"""
    return {"message": "LLM API聚合计费路由器服务运行中"}

@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}