import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 基本日志配置，可在 main.py 中通过 logging.basicConfig 调整级别
logger = logging.getLogger(__name__)

def retry_on_exception(func):
    """
    通用重试装饰器，针对可能抛出异常的函数（如网络请求、API 调用）。
    """
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapped
