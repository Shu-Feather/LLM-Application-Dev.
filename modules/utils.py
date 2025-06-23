# modules/utils.py

import time
import functools
import logging
from tenacity import retry as tenacity_retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_sync(times: int = 3, delay: int = 1):
    """
    通用同步重试装饰器，用于捕获 Exception 并重试的小函数。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, times+1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"尝试第{i}次失败: {e}")
                    if i < times:
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator

def retry_on_exception(func):
    """
    通用重试装饰器，针对可能抛出异常的函数（如网络请求、API 调用）。
    使用 tenacity，最多重试 3 次，指数退避。
    """
    @tenacity_retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapped
