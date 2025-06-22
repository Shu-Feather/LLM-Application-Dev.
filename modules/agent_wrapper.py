from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent

class CamelAgentWrapper:
    def __init__(self, temperature=0.7, model_name="gpt-3.5-turbo"):
        # 通过 ModelFactory 创建模型，根据 model_name 决定 Platform/Type
        # 这里示例直接使用字符串 model_name，CAMEL-AI 会使用默认平台
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_3_5_TURBO,
            model_config_dict=ChatGPTConfig(temperature=temperature).as_dict(),
        )
        self.agent = ChatAgent(system_message="You are a helpful assistant.", model=model)

    def step(self, user_input: str):
        # 执行一步对话
        response = self.agent.step(user_input)
        # response.msg.content 或 response.msgs 根据版本
        try:
            content = response.msg.content
        except AttributeError:
            # 兼容旧版/新版字段
            content = response.msgs[0].content if hasattr(response, 'msgs') else ""
        return content

    def reset(self):
        self.agent.reset()
