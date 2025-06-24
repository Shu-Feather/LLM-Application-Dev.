# scripts/batch_test.py
import sys
import os

# 添加项目根目录到系统路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

import json
import re
import logging
from modules.preprocessing import preprocess
from modules.llm_client import LLMClient
from modules.validator import validate_json, request_correction
from dotenv import load_dotenv

# 配置日志
log_dir = "test_results"
log_file_path = os.path.join(log_dir, "batch_test.log")
os.makedirs(log_dir, exist_ok=True) 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),  
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('batch_test')

load_dotenv()

def strip_code_block(text: str) -> str:
    """
    如果 LLM 返回带 Markdown 代码块（```json ...```），提取其中 JSON 部分。
    """
    # 匹配 ```json ... ``` 或 ``` ... ```
    pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
    m = pattern.search(text)
    if m:
        return m.group(1)
    return text

def load_inputs(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    input_path = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'sample_inputs.json')
    inputs = load_inputs(input_path)

    llm = LLMClient()
    results = []
    
    for idx, item in enumerate(inputs, 1):
        prompt = item.get("prompt", "")
        print(f"\n=== Testing Prompt #{idx} ===")
        print(f"Prompt: {prompt}")
        logger.info(f"Testing Prompt #{idx}: {prompt}")

        clean_prompt = preprocess(prompt)
        system_prompt = (
            "请基于用户输入生成有意义的 JSON，字段含义如下：\n"
            "- summary: 对请求的简要总结，字符串，不得为空；\n"
            "- details: 数组，每项为对象，包含 title(字符串) 和 content(字符串)；\n"
            "- metadata: 对象，包含 generated_at(UTC 时间字符串) 和 confidence(0.0-1.0 数字)；\n"
            "- 可选字段: recommendations(数组), images(数组), source(字符串) 等；\n"
            "仅输出合法 JSON，不要额外注释或代码块标记。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_prompt}
        ]

        # 发起流式请求
        print("Response:")
        try:
            raw_output = llm.chat_stream(messages)
        except Exception as e:
            print(f"LLM call error: {e}")
            logger.error(f"LLM call error for prompt #{idx}: {e}")
            results.append({
                "prompt": prompt,
                "status": "error",
                "error": str(e)
            })
            continue

        # 去除 Markdown 代码块包裹
        raw_output_stripped = strip_code_block(raw_output).strip()
        
        # 解析 JSON
        try:
            parsed = json.loads(raw_output_stripped)
            results.append({
                "prompt": prompt,
                "status": "success",
                "response": parsed
            })
        except json.JSONDecodeError:
            logger.warning(f"Output is not valid JSON for prompt #{idx}. Requesting correction...")
            try:
                corrected_str = request_correction(llm, raw_output_stripped, clean_prompt)
                corrected_str = strip_code_block(corrected_str).strip()
                parsed = json.loads(corrected_str)
                results.append({
                    "prompt": prompt,
                    "status": "corrected",
                    "original_response": raw_output_stripped,
                    "corrected_response": parsed
                })
                logger.info(f"Corrected response for prompt #{idx}")
            except Exception as e:
                logger.error(f"Correction failed: {e}")
                results.append({
                    "prompt": prompt,
                    "status": "error",
                    "error": f"Correction failed: {str(e)}"
                })
                continue

        # 后台静默校验结构
        valid, err = validate_json(parsed)
        if not valid:
            logger.warning(f"JSON validation failed for prompt #{idx}: {err}")
            # 尝试后台修正
            try:
                corrected = request_correction(llm, raw_output_stripped, clean_prompt)
                corrected = strip_code_block(corrected).strip()
                try:
                    parsed2 = json.loads(corrected)
                    valid2, err2 = validate_json(parsed2)
                    if valid2:
                        logger.info(f"Background correction successful for prompt #{idx}")
                    else:
                        logger.error(f"Background correction still invalid: {err2}")
                except Exception:
                    logger.error("Background correction: parse failed")
            except Exception as e:
                logger.error(f"Background correction failed: {e}")

    # 保存测试结果
    result_path = os.path.join(os.path.dirname(__file__), '..', 'test_results', 'batch_results.json')
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n=== Batch Test Completed ===")
    print(f"Results saved to: {result_path}")

if __name__ == '__main__':
    main()