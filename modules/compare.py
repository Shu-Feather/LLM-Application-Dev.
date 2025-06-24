# modules/compare.py
from modules.llm_client import LLMClient
from modules.preprocessing import preprocess
import json

def compare_params(prompt: str, model_name: str = 'gpt-3.5-turbo'):
    """
    对比不同参数组合对 LLM 输出的影响。
    """
    from modules.validator import load_schema
    schema = load_schema()
    schema_str = json.dumps(schema, ensure_ascii=False)
    # 使用与main.py相同的系统提示
    system_prompt = (
        "请基于用户输入生成有意义的 JSON，字段含义如下：\n"
        "- summary: 对请求的简要总结，字符串，不得为空；\n"
        "- details: 数组，每项为对象，包含 title(字符串) 和 content(字符串)；\n"
        "- metadata: 对象，包含 generated_at(UTC 时间字符串) 和 confidence(0.0-1.0 数字)；\n"
        "- 可选字段: recommendations(数组), images(数组), source(字符串) 等；\n"
        f"Schema: {schema_str}\n"
        "仅输出合法 JSON，不要额外注释或代码块标记。"
    )
    # 使用与main.py相同的预处理
    from modules.preprocessing import preprocess
    sanitized = preprocess(prompt)
    
    # 统一消息格式
    base_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": sanitized}
    ]

    llm = LLMClient(model_name=model_name)
    # 参数组合列表，可根据需要增减或调整
    param_sets = [
        {'temperature': 0.3, 'top_p': 1.0},
        {'temperature': 0.7, 'top_p': 1.0},
        {'temperature': 1.0, 'top_p': 1.0},
        {'temperature': 0.7, 'top_p': 0.8},
        {'temperature': 0.7, 'top_p': 0.5},
        {'temperature': 0.7, 'top_p': 1.0, 'presence_penalty': 0.0, 'frequency_penalty': 0.0},
        {'temperature': 0.7, 'top_p': 1.0, 'presence_penalty': 0.5, 'frequency_penalty': 0.5},
        # 可以加入 max_tokens、stop、其他参数
        # {'temperature': 0.7, 'top_p': 1.0, 'max_tokens': 100},
    ]
    
    results = []
    for params in param_sets:
        print(f"\n--- Testing params: {params} ---")
        try:
            out = llm.chat_stream(base_messages, **params)
        except Exception as e:
            print(f"调用出错: {e}")
            out = ""
        print("Result:", out)
        results.append((params, out))

    return results
