import argparse
import json
import logging
from modules.preprocessing import preprocess
from modules.llm_client import LLMClient
from modules.validator import validate_json, request_correction

logger = logging.getLogger(__name__)

def run_cli():
    parser = argparse.ArgumentParser(description="基础 LLM 应用 CLI")
    parser.add_argument('--model', type=str, default='gpt-3.5-turbo', help='模型名称')
    parser.add_argument('--temp', type=float, default=0.7, help='temperature 参数')
    parser.add_argument('--top_p', type=float, default=1.0, help='top_p 参数')
    parser.add_argument('--compare', action='store_true', help='对比不同 temperature 输出')
    parser.add_argument('--use_agent', action='store_true', help='使用 CAMEL Agent')
    args = parser.parse_args()

    llm = LLMClient(model_name=args.model)

    if args.compare:
        prompt = input("请输入用于对比的 Prompt: ")
        prompt = preprocess(prompt)
        llm.compare_temperature(prompt)
        return

    # Agent 部分略...

    while True:
        user_input = input("\n输入你的请求 (输入 'exit' 退出): ")
        if user_input.lower() in ('exit', 'quit'):
            break
        clean_input = preprocess(user_input)
        if not clean_input.strip():
            print("输入为空或被过滤， 请重新输入更具体的请求。")
            continue

        # 更详细的 system_prompt，指导生成有意义内容
        system_prompt = (
            "请基于用户输入生成有意义的 JSON，字段含义如下：\n"
            "- summary: 对用户输入的总结或回应（非空）。\n"
            "- details: 进一步的信息列表，根据上下文生成示例或建议。\n"
            "- metadata.generated_at: 当前 UTC 时间，格式 YYYY-MM-DDTHH:MM:SSZ。\n"
            "- metadata.confidence: 0.0-1.0 之间的估计值，反映对生成内容的信心。\n"
            "仅输出合法 JSON，不要额外注释或代码块标记。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_input}
        ]
        print("开始请求 LLM，流式输出如下：")
        try:
            raw_out = llm.chat_stream(messages, temperature=args.temp, top_p=args.top_p)
        except Exception as e:
            logger.error(f"LLM 调用异常: {e}")
            continue

        # JSON 校验与修正
        try:
            parsed = json.loads(raw_out)
            valid, err = validate_json(parsed)
        except Exception:
            valid = False
            err = "JSON 解析失败"
        if not valid:
            print(f"输出不符合 Schema: {err}，正在请求修正……")
            try:
                corrected = request_correction(llm, raw_out, clean_input)
                print("修正后输出：")
                print(corrected)
            except Exception as e:
                logger.error(f"修正过程异常: {e}")
        else:
            print("输出符合 Schema，可进一步处理或保存：")
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
            # 可保存或其他后续流程
