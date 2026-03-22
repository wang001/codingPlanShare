import unittest
import threading
import time
from app.utils.cache import cache

class TestConcurrentCache(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        # 清空缓存
        cache.clear()
    
    def tearDown(self):
        """清理测试环境"""
        # 清空缓存
        cache.clear()
    
    def test_concurrent_different_keys(self):
        """测试并发操作不同的缓存键"""
        def set_key1():
            """设置键1的值"""
            for _ in range(1000):
                current = cache.get("key1") or 0
                cache.set("key1", current + 1)
        
        def set_key2():
            """设置键2的值"""
            for _ in range(1000):
                current = cache.get("key2") or 0
                cache.set("key2", current + 1)
        
        def set_key3():
            """设置键3的值"""
            for _ in range(1000):
                current = cache.get("key3") or 0
                cache.set("key3", current + 1)
        
        # 创建线程
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=set_key1))
            threads.append(threading.Thread(target=set_key2))
            threads.append(threading.Thread(target=set_key3))
        
        # 启动线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        expected_key1 = 5000  # 5个线程，每个执行1000次
        expected_key2 = 5000  # 5个线程，每个执行1000次
        expected_key3 = 5000  # 5个线程，每个执行1000次
        
        actual_key1 = cache.get("key1")
        actual_key2 = cache.get("key2")
        actual_key3 = cache.get("key3")
        
        self.assertEqual(actual_key1, expected_key1)
        self.assertEqual(actual_key2, expected_key2)
        self.assertEqual(actual_key3, expected_key3)
    
    def test_concurrent_same_key(self):
        """测试并发操作同一个缓存键"""
        def increment_key():
            """增加键的值"""
            for _ in range(1000):
                current = cache.get("shared_key") or 0
                cache.set("shared_key", current + 1)
        
        # 创建10个线程并发操作同一个键
        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=increment_key))
        
        # 启动线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        expected_value = 10000  # 10个线程，每个执行1000次
        actual_value = cache.get("shared_key")
        
        self.assertEqual(actual_value, expected_value)
    
    def test_mixed_operations(self):
        """测试混合操作（同时有增加和减少）"""
        def increment_key():
            """增加键的值"""
            for _ in range(500):
                current = cache.get("mixed_key") or 0
                cache.set("mixed_key", current + 1)
        
        def decrement_key():
            """减少键的值"""
            for _ in range(300):
                current = cache.get("mixed_key") or 0
                cache.set("mixed_key", current - 1)
        
        # 创建线程
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=increment_key))
            threads.append(threading.Thread(target=decrement_key))
        
        # 启动线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        expected_value = (5 * 500) - (5 * 300)  # 5个线程加500次，5个线程减300次
        actual_value = cache.get("mixed_key")
        
        self.assertEqual(actual_value, expected_value)

if __name__ == '__main__':
    unittest.main()