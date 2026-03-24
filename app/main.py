from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import auth, users, keys, points, chat, embeddings, admin
from app.utils.background_tasks import background_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用生命周期管理。

    startup：启动积分落库后台任务
    shutdown：优雅停机 —— 等待当前 flush 完成，再做一次最终 flush，确保不丢数据
    """
    # ── startup ──
    await background_tasks.start()

    yield  # 应用正常运行期间在这里挂起

    # ── shutdown（收到 SIGTERM 后触发）──
    await background_tasks.stop()


app = FastAPI(
    title="LLM API聚合计费路由器",
    description="一个轻量级的LLM API聚合计费路由器，支持多厂商API适配、积分计费、密钥管理等功能",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["认证"])
app.include_router(users.router,      prefix="/api/v1/users",      tags=["用户"])
app.include_router(keys.router,       prefix="/api/v1/keys",       tags=["密钥"])
app.include_router(points.router,     prefix="/api/v1/points",     tags=["积分"])
app.include_router(chat.router,       prefix="/api/v1/chat",       tags=["聊天"])
app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["嵌入"])
app.include_router(admin.router,      prefix="/api/admin",         tags=["管理员"])


@app.get("/")
def read_root():
    return {"message": "LLM API聚合计费路由器服务运行中"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
