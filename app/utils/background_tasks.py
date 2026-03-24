"""
后台任务管理器
==============

职责：
  1. 每秒调用 flush_to_db()，将内存积分变动批量落库
  2. 响应优雅停机信号（SIGTERM / lifespan shutdown）：
     - 标记停止，等待当前 flush 完成
     - 再做一次最终 flush，确保不丢进行中的数据

优雅停机流程（配合 FastAPI lifespan）：
  SIGTERM → FastAPI 不再接受新请求 → lifespan shutdown 触发
  → background_tasks.stop() 被 await
  → 等待正在进行的 flush 结束（最多 2 秒）
  → 执行最终 flush（把停机前最后积累的记录全部落库）
  → 退出
"""

import asyncio
import logging
from app.services.points_service import flush_to_db

logger = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 1   # 正常刷新间隔
STOP_TIMEOUT_SECONDS = 5     # 优雅停机最长等待时间


class BackgroundTasks:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._flush_in_progress = False

    async def start(self):
        """启动后台刷新任务（在 FastAPI lifespan startup 时调用）。"""
        self._running = True
        self._task = asyncio.create_task(self._flush_loop(), name="points-flush")
        logger.info("[BackgroundTasks] 积分落库后台任务已启动，刷新间隔 %ds", FLUSH_INTERVAL_SECONDS)

    async def stop(self):
        """
        优雅停机（在 FastAPI lifespan shutdown 时调用）。

        步骤：
          1. 发出停止信号，等待当前 flush 周期自然结束
          2. 做一次最终 flush，清空所有待落库记录
          3. 取消后台 task
        """
        logger.info("[BackgroundTasks] 收到停机信号，准备优雅退出...")
        self._running = False

        # 等待后台 task 自然退出（最多 STOP_TIMEOUT_SECONDS 秒）
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=STOP_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.warning("[BackgroundTasks] 后台 task 超时，强制取消")
                self._task.cancel()
            except asyncio.CancelledError:
                pass

        # 最终 flush：确保停机前所有积分记录都落库
        logger.info("[BackgroundTasks] 执行最终落库 flush...")
        await self._do_flush()
        logger.info("[BackgroundTasks] 最终 flush 完成，安全退出")

    async def _flush_loop(self):
        """后台主循环：每 FLUSH_INTERVAL_SECONDS 秒 flush 一次。"""
        while self._running:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            if self._running:   # 睡醒后再检查一次，避免停机时多余的 flush
                await self._do_flush()

    async def _do_flush(self):
        """
        在 asyncio 线程池中执行同步的 flush_to_db()，
        不阻塞事件循环，保证 FastAPI 正常处理其他请求。
        """
        self._flush_in_progress = True
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, flush_to_db)
        except Exception as e:
            logger.error("[BackgroundTasks] flush 异常: %s", e)
        finally:
            self._flush_in_progress = False


# 全局单例，由 app/main.py 的 lifespan 管理生命周期
background_tasks = BackgroundTasks()
