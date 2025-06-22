import os
import json
import logging
from jsonschema import validate, ValidationError
from datetime import datetime

logger = logging.getLogger(__name__)

# 计算项目根目录并定位 schema.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
schema_path = os.path.join(BASE_DIR, 'config', 'schema.json')

try:
    with open(schema_path, encoding='utf-8') as f:
        SCHEMA = json.load(f)
    logger.info(f"成功加载 JSON Schema: {schema_path}")
except FileNotFoundError:
    logger.error(f"未找到 schema 文件: {schema_path}")
    SCHEMA = None
except json.JSONDecodeError as e:
    logger.error(f"读取 schema 时 JSONDecodeError: {e}")
    SCHEMA = None

def validate_json(obj):
    if SCHEMA is None:
        msg = "JSON Schema 未加载，无法校验。"
        logger.error(msg)
        return False, msg
    try:
        validate(instance=obj, schema=SCHEMA)
        return True, None
    except ValidationError as e:
        return False, e.message

def request_correction(llm_client, raw_output: str, user_input: str, max_retries: int = 2):
    """
    当 JSON 校验失败时，多次向 LLM 请求修正，直到符合 Schema 或达到重试次数。
    user_input: 原始用户请求，用于提示上下文。
    """
    if SCHEMA is None:
        logger.error("JSON Schema 未加载，跳过修正。")
        return raw_output

    def prompt_for_correction(message: str, user_input: str):
        current_ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            "以下内容需输出符合 JSON Schema，并基于用户输入生成有意义内容：\n"
            f"用户输入: {user_input}\n"
            f"Schema: {json.dumps(SCHEMA, ensure_ascii=False)}\n"
            f"{message}\n"
            f"注意：metadata.generated_at 应为当前 UTC 时间，如 {current_ts}。\n"
            "请严格输出合法 JSON，不要空字段，不要额外注释或代码块标记。"
        )

    for attempt in range(1, max_retries + 1):
        try:
            parsed = json.loads(raw_output)
            valid, err = validate_json(parsed)
            if valid:
                return raw_output
            else:
                logger.warning(f"第{attempt}次修正: JSON 校验失败，错误: {err}")
                prompt = prompt_for_correction(f"原始内容: {raw_output}\n错误信息: {err}", user_input)
        except json.JSONDecodeError as e:
            logger.warning(f"第{attempt}次修正: 不是合法 JSON: {e}")
            prompt = prompt_for_correction(f"原始内容: {raw_output}\n解析错误: {e}", user_input)

        corrected = llm_client.chat_stream(
            messages=[
                {"role": "system", "content": "你是 JSON 修正助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        raw_output = corrected

    # 最后一轮校验
    try:
        parsed = json.loads(raw_output)
        valid, err = validate_json(parsed)
        if valid:
            return raw_output
        else:
            logger.error(f"修正后仍不符合 Schema: {err}")
    except json.JSONDecodeError as e:
        logger.error(f"修正后仍不是合法 JSON: {e}")
    return raw_output
