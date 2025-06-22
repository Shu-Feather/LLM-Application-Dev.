import os
import openai
from dotenv import load_dotenv
import sys
from modules.utils import retry_on_exception

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class LLMClient:
    def __init__(self, model_name="gpt-3.5-turbo"):
        self.model = model_name

    @retry_on_exception
    def chat_stream(self, messages, temperature=0.7, top_p=1.0):
        """
        使用 OpenAI Python SDK v1 的流式接口逐块返回内容，实现打字机效果。
        """
        response = openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            stream=True
        )
        collected = ""
        for chunk in response:
            # chunk.choices[0].delta 是一个对象，属性 content 存放文本
            delta_obj = chunk.choices[0].delta
            # 有时 delta_obj 可能没有 content（如只是 role 信息），所以用 getattr 安全获取
            delta = getattr(delta_obj, "content", "")
            if delta:
                collected += delta
                sys.stdout.write(delta)
                sys.stdout.flush()
        print()  # 最后换行
        return collected

    @retry_on_exception
    def chat_once(self, messages, temperature=0.7, top_p=1.0):
        """
        非流式一次性调用，仅用于对比或测试，不作为主流程。
        """
        response = openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            stream=False
        )
        # 直接访问 message.content
        return response.choices[0].message.content

    def compare_temperature(self, user_prompt: str, system_prompt="You are a helpful assistant."):
        """
        演示不同 temperature 对输出的影响，对比流式结果。
        """
        base_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        print("=== Temperature=0.7 流式输出 ===")
        out1 = self.chat_stream(base_messages, temperature=0.7)
        print("返回内容（temperature=0.7）:", out1)
        print("\n=== Temperature=1.2 流式输出 ===")
        out2 = self.chat_stream(base_messages, temperature=1.2)
        print("返回内容（temperature=1.2）:", out2)
