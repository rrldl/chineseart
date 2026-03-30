#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能优化模块 - 实现缓存、异步处理、批处理等功能
"""
import os
import json
import pickle
import threading
import queue
import time
from functools import wraps
from datetime import datetime, timedelta

class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir="./data/cache", max_size=1000, expiration=24):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            max_size: 最大缓存数量
            expiration: 缓存过期时间（小时）
        """
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.expiration = expiration
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存索引
        self.cache_index = {}
        self._load_cache_index()
        
        # 清理过期缓存
        self._clean_expired_cache()

    def _load_cache_index(self):
        """加载缓存索引"""
        index_path = os.path.join(self.cache_dir, "cache_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    self.cache_index = json.load(f)
            except Exception as e:
                print(f"加载缓存索引失败: {e}")
                self.cache_index = {}

    def _save_cache_index(self):
        """保存缓存索引"""
        index_path = os.path.join(self.cache_dir, "cache_index.json")
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存索引失败: {e}")

    def _clean_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, info in self.cache_index.items():
            if current_time - info["timestamp"] > self.expiration * 3600:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._delete_cache(key)
        
        # 如果缓存数量超过最大值，删除最旧的缓存
        if len(self.cache_index) > self.max_size:
            sorted_keys = sorted(self.cache_index.keys(), 
                              key=lambda k: self.cache_index[k]["timestamp"])
            to_delete = sorted_keys[:len(self.cache_index) - self.max_size]
            for key in to_delete:
                self._delete_cache(key)
        
        self._save_cache_index()

    def _delete_cache(self, key):
        """删除缓存"""
        if key in self.cache_index:
            cache_path = os.path.join(self.cache_dir, f"{key}.pkl")
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception as e:
                    print(f"删除缓存文件失败: {e}")
            del self.cache_index[key]

    def get(self, key):
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            object: 缓存值
        """
        if key not in self.cache_index:
            return None
        
        # 检查是否过期
        current_time = time.time()
        if current_time - self.cache_index[key]["timestamp"] > self.expiration * 3600:
            self._delete_cache(key)
            return None
        
        # 加载缓存
        cache_path = os.path.join(self.cache_dir, f"{key}.pkl")
        if not os.path.exists(cache_path):
            del self.cache_index[key]
            return None
        
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"加载缓存失败: {e}")
            self._delete_cache(key)
            return None

    def set(self, key, value):
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        # 清理过期缓存
        self._clean_expired_cache()
        
        # 保存缓存
        cache_path = os.path.join(self.cache_dir, f"{key}.pkl")
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)
            
            # 更新索引
            self.cache_index[key] = {
                "timestamp": time.time(),
                "size": os.path.getsize(cache_path)
            }
            self._save_cache_index()
            return True
        except Exception as e:
            print(f"保存缓存失败: {e}")
            return False

    def clear(self):
        """清空缓存"""
        for key in list(self.cache_index.keys()):
            self._delete_cache(key)
        self._save_cache_index()

class AsyncProcessor:
    """异步处理器"""

    def __init__(self, max_workers=4):
        """
        初始化异步处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.running = False
        
        # 启动工作线程
        self.start()

    def start(self):
        """启动工作线程"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

    def stop(self):
        """停止工作线程"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=1)
        self.workers = []

    def _worker(self):
        """工作线程"""
        while self.running:
            try:
                task_id, func, args, kwargs = self.task_queue.get(timeout=0.1)
                try:
                    result = func(*args, **kwargs)
                    self.result_queue.put((task_id, result, None))
                except Exception as e:
                    self.result_queue.put((task_id, None, e))
                finally:
                    self.task_queue.task_done()
            except queue.Empty:
                continue

    def submit(self, func, *args, **kwargs):
        """
        提交任务
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            str: 任务ID
        """
        task_id = f"task_{int(time.time() * 1000)}"
        self.task_queue.put((task_id, func, args, kwargs))
        return task_id

    def get_result(self, task_id, timeout=None):
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间
            
        Returns:
            tuple: (result, error)
        """
        start_time = time.time()
        while timeout is None or time.time() - start_time < timeout:
            try:
                result_id, result, error = self.result_queue.get(timeout=0.1)
                if result_id == task_id:
                    return result, error
                else:
                    # 不是目标任务，放回队列
                    self.result_queue.put((result_id, result, error))
            except queue.Empty:
                continue
        return None, TimeoutError("任务执行超时")

class BatchProcessor:
    """批处理器"""

    def __init__(self, batch_size=10):
        """
        初始化批处理器
        
        Args:
            batch_size: 批处理大小
        """
        self.batch_size = batch_size
        self.tasks = []

    def add_task(self, task):
        """
        添加任务
        
        Args:
            task: 任务
        """
        self.tasks.append(task)
        
        # 如果任务数量达到批处理大小，执行批处理
        if len(self.tasks) >= self.batch_size:
            return self.process_batch()
        return None

    def process_batch(self):
        """
        执行批处理
        
        Returns:
            list: 处理结果
        """
        if not self.tasks:
            return []
        
        # 执行批处理
        results = []
        try:
            # 这里可以根据具体任务类型实现不同的批处理逻辑
            for task in self.tasks:
                if isinstance(task, dict) and "func" in task:
                    func = task["func"]
                    args = task.get("args", ())
                    kwargs = task.get("kwargs", {})
                    results.append(func(*args, **kwargs))
                else:
                    results.append(None)
        except Exception as e:
            print(f"批处理失败: {e}")
            results = [None] * len(self.tasks)
        
        # 清空任务队列
        self.tasks = []
        
        return results

    def flush(self):
        """
        执行剩余任务
        
        Returns:
            list: 处理结果
        """
        return self.process_batch()

# 装饰器

def cached(cache_key_func=None, expiration=24):
    """
    缓存装饰器
    
    Args:
        cache_key_func: 缓存键生成函数
        expiration: 过期时间（小时）
    """
    cache_manager = CacheManager(expiration=expiration)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                key = cache_key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(key, result)
            
            return result
        return wrapper
    return decorator

# 全局实例
cache_manager = CacheManager()
async_processor = AsyncProcessor()
batch_processor = BatchProcessor()

# 工具函数
def generate_cache_key(prefix, *args, **kwargs):
    """
    生成缓存键
    
    Args:
        prefix: 前缀
        *args: 参数
        **kwargs: 关键字参数
        
    Returns:
        str: 缓存键
    """
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    return "_".join(key_parts).replace(" ", "_").replace("/", "_")

# 测试代码
if __name__ == "__main__":
    print("测试缓存管理器...")
    
    # 测试缓存
    cache_manager.set("test_key", "test_value")
    value = cache_manager.get("test_key")
    print(f"缓存测试: {value}")
    
    # 测试异步处理
    print("\n测试异步处理器...")
    
    def test_func(x, y):
        time.sleep(1)
        return x + y
    
    task_id = async_processor.submit(test_func, 1, 2)
    result, error = async_processor.get_result(task_id, timeout=2)
    print(f"异步处理测试: {result}")
    
    # 测试批处理
    print("\n测试批处理器...")
    
    for i in range(5):
        batch_processor.add_task({
            "func": lambda x: x * 2,
            "args": (i,)
        })
    
    results = batch_processor.flush()
    print(f"批处理测试: {results}")
    
    # 测试装饰器
    print("\n测试缓存装饰器...")
    
    @cached()
    def expensive_function(x):
        print(f"执行昂贵函数: {x}")
        time.sleep(1)
        return x * x
    
    # 第一次执行
    start_time = time.time()
    result1 = expensive_function(5)
    print(f"第一次执行结果: {result1}, 耗时: {time.time() - start_time:.2f}秒")
    
    # 第二次执行（应该从缓存获取）
    start_time = time.time()
    result2 = expensive_function(5)
    print(f"第二次执行结果: {result2}, 耗时: {time.time() - start_time:.2f}秒")
    
    print("性能优化模块测试完成！")
