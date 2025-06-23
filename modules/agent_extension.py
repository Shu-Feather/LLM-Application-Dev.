import os
import re
import openai
from .tool_integration import CalculatorTool, DatabaseTool, APITool, PythonInterpreterTool
from .rag import RAGRetriever, augment_query_with_rag
from .memory_manager import MemoryManager

class AdvancedAgent:
    def __init__(self, user_id: str, rag: RAGRetriever=None):
        self.user_id = user_id
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4')
        self.calc = CalculatorTool()
        self.db = DatabaseTool()
        self.api = APITool()
        self.py = PythonInterpreterTool()
        self.mem = MemoryManager()
        self.rag = rag

    def decide_and_execute(self, user_input: str):
        self.mem.add_message(self.user_id, 'user', user_input)
        # Calculator
        if re.search(r"\b[0-9]+\s*[+\-*/]\s*[0-9]+", user_input):
            res = self.calc.eval_expr(user_input)
            self.mem.add_message(self.user_id, 'tool', f'calc: {res}')
            return f"Calculator result: {res}"
        # Database
        if re.search(r"\bselect\b|\binsert\b|\bupdate\b|\bdelete\b", user_input, re.IGNORECASE):
            res = self.db.execute(user_input)
            self.mem.add_message(self.user_id, 'tool', f'db: {res}')
            return f"Database result: {res}"
        # API
        if re.search(r"https?://", user_input):
            res = self.api.call('GET', user_input)
            self.mem.add_message(self.user_id, 'tool', f'api: {res}')
            return f"API result: {res}"
        # Code execution
        if '运行代码' in user_input or '执行代码' in user_input:
            code = user_input
            m = re.search(r"```(?:python)?\s*(.+?)```", user_input, re.DOTALL)
            if m:
                code = m.group(1)
            res = self.py.execute(code)
            self.mem.add_message(self.user_id, 'tool', f'py: {res}')
            return f"Code execution result: {res}"
        # RAG
        prompt = user_input
        if self.rag:
            prompt = augment_query_with_rag(user_input, self.rag)
        # LLM 调用，使用新版接口
        history = self.mem.get_history(self.user_id, limit=10)
        msgs = [{"role": "system", "content": "你是智能助手，结合工具和对话记忆回答。"}]
        for item in history:
            msgs.append({"role": item['role'], "content": item['content']})
        msgs.append({"role": "user", "content": prompt})
        # 注意新版接口
        resp = openai.chat.completions.create(
            model=self.llm_model,
            messages=msgs
        )
        ans = resp.choices[0].message.content.strip()
        self.mem.add_message(self.user_id, 'assistant', ans)
        return ans
