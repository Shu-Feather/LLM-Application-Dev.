# modules/llm_client.py
import os
import openai
from dotenv import load_dotenv
import sys
from modules.utils import retry_on_exception

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ANSI 颜色示例（可选）
GREEN = "\033[92m"
RESET = "\033[0m"

class LLMClient:
    def __init__(self, model_name="gpt-4"):
        self.model = model_name

    @retry_on_exception
    def chat_stream(self, messages, temperature=0.7, top_p=1.0, **kwargs):
        """
        流式调用，逐块打印（打字机效果），并返回完整文本。
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }
        params.update(kwargs)
        response = openai.chat.completions.create(**params)
        collected = ""
        # 打印前可输出提示
        sys.stdout.write(GREEN)  # 切换到绿色
        for chunk in response:
            delta = getattr(chunk.choices[0].delta, "content", "")
            if delta:
                collected += delta
                sys.stdout.write(delta)
                sys.stdout.flush()
        sys.stdout.write(RESET)  # 恢复颜色
        print()  # 最后换行
        return collected

    @retry_on_exception
    def chat_once(self, messages, temperature=0.7, top_p=1.0, **kwargs):
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        params.update(kwargs)
        response = openai.chat.completions.create(**params)
        return response.choices[0].message.content
