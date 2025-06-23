# modules/compare.py
from modules.llm_client import LLMClient
from modules.preprocessing import preprocess

def compare_params(prompt: str, model_name: str = 'gpt-3.5-turbo'):
    """
    对比不同参数组合对 LLM 输出的影响。
    """
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
    sanitized = preprocess(prompt)
    base_messages = [
        {"role": "system", "content": "请输出符合 JSON Schema 的结果，仅输出 JSON，不要额外注释。"},
        {"role": "user", "content": sanitized}
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
