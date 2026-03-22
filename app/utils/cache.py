import threading

class MemoryCache:
    """内存缓存实现"""
    def __init__(self):
        self._cache = {}
        self._expire_times = {}
        self._lock = threading.RLock()  # 全局锁，用于管理分段锁
        self._segment_locks = {}  # 分段锁字典
        self._num_segments = 16  # 分段数量
        
        # 初始化分段锁
        for i in range(self._num_segments):
            self._segment_locks[i] = threading.RLock()
    
    def _get_segment(self, key: str) -> int:
        """根据key获取分段索引"""
        return hash(key) % self._num_segments
    
    def _get_lock(self, key: str) -> threading.RLock:
        """根据key获取对应的分段锁"""
        segment = self._get_segment(key)
        return self._segment_locks[segment]
    
    def set(self, key: str, value, expire_seconds: int = None):
        """设置缓存"""
        with self._get_lock(key):
            self._cache[key] = value
            if expire_seconds:
                import time
                self._expire_times[key] = time.time() + expire_seconds
    
    def get(self, key: str):
        """获取缓存"""
        with self._get_lock(key):
            # 检查是否过期
            import time
            if key in self._expire_times and time.time() > self._expire_times[key]:
                del self._cache[key]
                del self._expire_times[key]
                return None
            return self._cache.get(key)
    
    def delete(self, key: str):
        """删除缓存"""
        with self._get_lock(key):
            if key in self._cache:
                del self._cache[key]
            if key in self._expire_times:
                del self._expire_times[key]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._expire_times.clear()
    
    def get_all_keys(self):
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())

# 创建全局缓存实例
cache = MemoryCache()