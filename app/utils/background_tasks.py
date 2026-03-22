import asyncio
import time
from typing import Dict
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.utils.cache import cache

class BackgroundTasks:
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """启动后台任务"""
        self.running = True
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """停止后台任务"""
        self.running = False
        if self.task:
            await self.task
    
    async def _run(self):
        """后台任务主循环"""
        while self.running:
            try:
                # 每1秒执行一次
                await self._sync_cache_to_db()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"后台任务出错: {e}")
                await asyncio.sleep(1)
    
    async def _sync_cache_to_db(self):
        """将缓存中的数据同步到数据库"""
        db = SessionLocal()
        try:
            # 同步用户积分余额
            await self._sync_user_balances(db)
        finally:
            db.close()
    
    async def _sync_user_balances(self, db: Session):
        """同步用户积分余额"""
        # 获取所有缓存的用户余额
        user_balances = {}
        for key in cache.get_all_keys():
            if key.startswith("user:balance:"):
                user_id = int(key.split(":")[-1])
                user_balances[user_id] = cache.get(key)
        
        # 同步到数据库
        for user_id, balance in user_balances.items():
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.balance != balance:
                    user.balance = balance
                    db.commit()
            except Exception as e:
                print(f"同步用户 {user_id} 积分失败: {e}")
                db.rollback()

# 创建全局后台任务实例
background_tasks = BackgroundTasks()