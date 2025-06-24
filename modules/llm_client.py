import time
import os
import openai
from dotenv import load_dotenv
import sys
from modules.utils import retry_on_exception

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ANSI 颜色代码
GREEN = "\033[92m"
RESET = "\033[0m"

class LLMClient:
    def __init__(self, model_name="gpt-4"):
        self.model = model_name

    @retry_on_exception
    def chat_stream(self, messages, temperature=0.7, top_p=1.0, **kwargs):
        """
        流式调用，实现打字机效果
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
        """
        非流式调用，但输出时模拟流式效果
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        params.update(kwargs)
        response = openai.chat.completions.create(**params)
        content = response.choices[0].message.content
        
        # 模拟流式输出效果
        sys.stdout.write(GREEN)
        for char in content:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.01) 
        sys.stdout.write(RESET)
        print()
        
        return content