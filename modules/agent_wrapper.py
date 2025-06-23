from .agent_extension import AdvancedAgent

class AdvancedAgentWrapper:
    def __init__(self, temperature=0.7, model_name="gpt-3.5-turbo", use_rag: bool=False, rag_index: str=None, rag_docs: str=None):
        # 可设置环境变量或直接在 AdvancedAgent 中使用 LLM_MODEL
        os.environ['LLM_MODEL'] = model_name
        from .rag import RAGRetriever
        rag = None
        if use_rag:
            rag = RAGRetriever(index_prefix=rag_index) if rag_index else RAGRetriever()
            if rag_docs:
                import json
                try:
                    docs = json.load(open(rag_docs, 'r', encoding='utf-8'))
                    rag.build_index(docs)
                except Exception:
                    pass
        self.agent = AdvancedAgent(user_id='agent_user', rag=rag)
    def handle(self, user_input: str) -> str:
        return self.agent.decide_and_execute(user_input)

# 可选 Camel-AI 集成示例
# from camel.models import ModelFactory
# from camel.types import ModelPlatformType, ModelType
# from camel.configs import ChatGPTConfig
# from camel.agents import ChatAgent
#
# class CamelAgentWrapper:
#     def __init__(self, temperature=0.7, model_name="gpt-3.5-turbo"):
#         model = ModelFactory.create(
#             model_platform=ModelPlatformType.OPENAI,
#             model_type=ModelType.GPT_3_5_TURBO,
#             model_config_dict=ChatGPTConfig(temperature=temperature).as_dict(),
#         )
#         self.agent = ChatAgent(system_message="You are a helpful assistant.", model=model)
#     def step(self, user_input: str):
#         response = self.agent.step(user_input)
#         try:
#             content = response.msg.content
#         except AttributeError:
#             content = response.msgs[0].content if hasattr(response, 'msgs') else ""
#         return content
#     def reset(self):
#         self.agent.reset()