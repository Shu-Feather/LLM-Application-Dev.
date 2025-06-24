import os
import re
import openai
import json
import logging
from .tool_integration import CalculatorTool, DatabaseTool, APITool, PythonInterpreterTool
from .rag import RAGRetriever, augment_query_with_rag
from .memory_manager import MemoryManager
from .multimodal import MultiModalProcessor
from .utils import retry_sync

logger = logging.getLogger(__name__)

class AdvancedAgent:
    def __init__(self, user_id: str, rag: RAGRetriever = None):
        self.user_id = user_id
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4o')
        self.calc = CalculatorTool()
        self.db = DatabaseTool()
        self.api = APITool()
        self.py = PythonInterpreterTool()
        self.mem = MemoryManager()
        self.rag = rag
        self.multimodal = MultiModalProcessor()
        
        # 工具描述，用于LLM决策
        self.tools = [
            {
                "name": "calculator",
                "description": "执行数学计算和表达式求值",
                "pattern": r"计算|算一下|等于多少|\d+\s*[\+\-\*/]\s*\d+",
                "examples": ["计算2+3*5", "圆周率乘以半径的平方", "sin(30度)等于多少"]
            },
            {
                "name": "database",
                "description": "执行SQL数据库查询",
                "pattern": r"查询|SELECT|INSERT|UPDATE|DELETE|FROM|WHERE",
                "examples": ["查询所有用户信息", "SELECT * FROM users WHERE age > 30"]
            },
            {
                "name": "api",
                "description": "调用外部API获取数据",
                "pattern": r"API|调用|获取数据|https?://|天气|股票|新闻",
                "examples": ["获取纽约的天气", "调用GitHub API获取仓库信息"]
            },
            {
                "name": "python",
                "description": "执行Python代码",
                "pattern": r"运行代码|执行程序|写一个|python|脚本|算法",
                "examples": ["写一个计算斐波那契数列的Python函数", "执行这段代码"]
            },
            {
                "name": "multimodal",
                "description": "处理图像或音频输入",
                "pattern": r"图片|图像|照片|音频|语音|录音|识别|描述",
                "examples": ["描述这张图片", "把这段语音转成文字"]
            }
        ]

    def decide_tool_usage(self, user_input: str) -> str:
        """
        决策逻辑1：基于规则的模式匹配
        使用预定义模式检测用户意图
        """
        for tool in self.tools:
            if re.search(tool["pattern"], user_input, re.IGNORECASE):
                return tool["name"]
        return "llm"

    @retry_sync(times=2, delay=1)
    def llm_decide_tool(self, user_input: str, history: list) -> str:
        """
        决策逻辑2：使用LLM进行工具选择
        """
        # 构建工具描述
        tool_descriptions = "\n".join(
            [f"{tool['name']}: {tool['description']} (例如: {', '.join(tool['examples'])})" 
             for tool in self.tools]
        )
        
        # 构建提示
        prompt = (
            f"用户输入: {user_input}\n\n"
            "请根据用户请求选择最合适的工具:\n"
            f"{tool_descriptions}\n"
            "llm: 直接回答问题（当没有合适工具时）\n\n"
            "请只返回工具名称，不要包含其他内容。"
        )
        
        messages = [
            {"role": "system", "content": "你是工具选择助手，根据用户请求选择最合适的工具。"},
            {"role": "user", "content": prompt}
        ]
        
        # 添加历史上下文
        if history:
            for item in history:
                messages.insert(-1, {"role": item['role'], "content": item['content']})
        
        # 调用LLM
        try:
            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=50
            )
            tool_name = response.choices[0].message.content.strip().lower()
            
            # 验证工具名称是否有效
            valid_tools = [t["name"] for t in self.tools] + ["llm"]
            return tool_name if tool_name in valid_tools else "llm"
        except Exception as e:
            logger.error(f"工具选择失败: {str(e)}")
            return "llm"

    def context_based_decision(self, user_input: str, history: list) -> str:
        """
        决策逻辑3：基于对话上下文的工具选择
        """
        # 检查最近对话中是否有工具使用
        recent_tools = []
        for msg in reversed(history[-5:]):  # 检查最近5条消息
            if msg['role'] == 'tool':
                recent_tools.append(msg['content'].split(':')[0])
        
        # 如果最近使用了工具，继续使用相同工具
        if recent_tools:
            last_tool = recent_tools[0]
            
            # 检查用户输入是否与上次工具相关
            if last_tool == "calculator" and re.search(r"\d+\s*[\+\-\*/]\s*\d+", user_input):
                return "calculator"
            elif last_tool == "database" and re.search(r"SELECT|FROM|WHERE", user_input, re.IGNORECASE):
                return "database"
            elif last_tool == "api" and re.search(r"API|调用|获取", user_input):
                return "api"
            elif last_tool == "python" and re.search(r"代码|运行|执行", user_input):
                return "python"
        
        return "llm"

    def execute_tool(self, tool_name: str, user_input: str) -> str:
        """执行选定的工具"""
        if tool_name == "calculator":
            return self.calc.calculate(user_input)
        elif tool_name == "database":
            return self.db.execute(user_input)
        elif tool_name == "api":
            # 尝试从用户输入中提取URL
            url_match = re.search(r'https?://[^\s]+', user_input)
            if url_match:
                return self.api.call('GET', url_match.group(0))
            else:
                return "API错误: 未提供有效的URL"
        elif tool_name == "python":
            # 尝试提取代码块
            code_match = re.search(r'```python(.*?)```', user_input, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                code = user_input
            return self.py.execute(code)
        elif tool_name == "multimodal":
            # 假设用户输入包含文件路径
            file_match = re.search(r'\b(\S+\.(png|jpg|jpeg|mp3|wav))\b', user_input)
            if file_match:
                file_path = file_match.group(1)
                if file_path.endswith(('.png', '.jpg', '.jpeg')):
                    return self.multimodal.process_image_input(file_path)
                elif file_path.endswith(('.mp3', '.wav')):
                    return self.multimodal.process_audio_input(file_path)
            return "多模态错误: 未提供有效的文件路径"
        else:
            return f"未知工具: {tool_name}"

    def decide_and_execute(self, user_input: str):
        # 添加到记忆
        self.mem.add_message(self.user_id, 'user', user_input)
        
        # 获取对话历史
        history = self.mem.get_history(self.user_id, limit=10)
        
        # 决策层级1: 基于规则的快速决策
        tool_name = self.decide_tool_usage(user_input)
        
        # 决策层级2: 基于上下文的决策
        if tool_name == "llm":
            tool_name = self.context_based_decision(user_input, history)
        
        # 决策层级3: 使用LLM进行智能决策
        if tool_name == "llm":
            tool_name = self.llm_decide_tool(user_input, history)
        
        logger.info(f"选择工具: {tool_name} 用于输入: {user_input}")
        
        # 执行工具或LLM
        if tool_name != "llm":
            try:
                result = self.execute_tool(tool_name, user_input)
                self.mem.add_message(self.user_id, 'tool', f'{tool_name}: {result}')
                return f"{tool_name.capitalize()} 结果: {result}"
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {str(e)}")
                # 失败时回退到LLM
                tool_name = "llm"
        
        # 使用LLM生成响应
        if tool_name == "llm":
            prompt = user_input
            if self.rag:
                prompt = augment_query_with_rag(user_input, self.rag)
            
            messages = [{"role": "system", "content": "你是智能助手，结合工具和对话记忆回答。"}]
            for item in history:
                messages.append({"role": item['role'], "content": item['content']})
            messages.append({"role": "user", "content": prompt})
            
            try:
                resp = openai.chat.completions.create(
                    model=self.llm_model,
                    messages=messages
                )
                ans = resp.choices[0].message.content.strip()
                self.mem.add_message(self.user_id, 'assistant', ans)
                return ans
            except Exception as e:
                logger.error(f"LLM 调用失败: {str(e)}")
                return f"错误: 无法生成响应 - {str(e)}"