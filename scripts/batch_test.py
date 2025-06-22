import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.llm_client import LLMClient
from modules.validator import validate_json, request_correction
from dotenv import load_dotenv

load_dotenv()

def load_inputs(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    input_path = os.path.join('test_data', 'sample_inputs.json')
    inputs = load_inputs(input_path)

    llm = LLMClient()
    
    for idx, item in enumerate(inputs):
        prompt = item.get("prompt", "")
        print(f"\n=== Testing Prompt #{idx + 1} ===")
        print(f"Prompt: {prompt}")

        messages = [
            {"role": "system", "content": "你是一个智能 JSON 响应生成器，请根据用户需求返回符合 schema 的 JSON。"},
            {"role": "user", "content": prompt}
        ]

        raw_output = llm.chat_stream(messages)
        print("\nRaw Output:")
        print(raw_output)

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            print("Output is not valid JSON. Requesting correction...")
            parsed = json.loads(request_correction(llm, raw_output, prompt))

        valid, err = validate_json(parsed)
        if valid:
            print("Output valid against schema.")
        else:
            print(f"Output invalid: {err}")
            print("Requesting correction...")
            corrected = request_correction(llm, raw_output, prompt)
            print("Corrected Output:\n", corrected)

if __name__ == '__main__':
    main()
