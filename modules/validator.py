import os
import json
import logging
import jsonschema
import openai
from datetime import datetime
from .utils import retry_sync
import sys
import io

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCHEMA_PATH = os.path.join(BASE_DIR, 'config', 'schema.json')

def load_schema():
    path = os.getenv('SCHEMA_PATH') or DEFAULT_SCHEMA_PATH
    try:
        with open(path, encoding='utf-8') as f:
            schema = json.load(f)
        logger.info(f"成功加载 JSON Schema: {path}")
        return schema
    except Exception as e:
        logger.error(f"加载 Schema 失败: {e}")
    return None

def validate_json(obj: dict):
    schema = load_schema()
    if schema is None:
        msg = "JSON Schema 未加载，无法校验。"
        logger.error(msg)
        return False, msg
    try:
        jsonschema.validate(instance=obj, schema=schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, e.message

def request_correction(llm_client, raw_output: str, user_input: str, max_retries: int = 2):
    """静默修正 JSON 输出，不产生任何显示"""
    schema = load_schema()
    if schema is None:
        logger.error("JSON Schema 未加载，跳过修正。")
        return raw_output

    def prompt_for_correction(message: str):
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            "以下内容需输出符合 JSON Schema，并基于用户输入生成有意义内容：\n"
            f"用户输入: {user_input}\n"
            f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
            f"{message}\n"
            f"注意：metadata.generated_at 应为当前 UTC 时间，如 {ts}。\n"
            "请严格输出合法 JSON，不要空字段，不要额外注释或代码块标记。"
        )

    for attempt in range(1, max_retries + 1):
        try:
            parsed = json.loads(raw_output)
            valid, err = validate_json(parsed)
            if valid:
                return raw_output
            else:
                logger.info(f"静默修正 #{attempt}: JSON 校验失败 - {err}")
                prompt = prompt_for_correction(f"原始内容: {raw_output}\n错误信息: {err}")
        except json.JSONDecodeError as e:
            logger.info(f"静默修正 #{attempt}: 无效 JSON - {e}")
            prompt = prompt_for_correction(f"原始内容: {raw_output}\n解析错误: {e}")

        try:
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            # 使用非流式调用进行修正
            corrected = llm_client.chat_once(
                messages=[
                    {"role": "system", "content": "你是 JSON 修正助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            # 恢复 stdout
            sys.stdout = original_stdout
        except Exception as e:
            logger.error(f"静默修正失败: {e}")
            # 恢复 stdout
            sys.stdout = original_stdout
            break
            
        raw_output = corrected
        logger.info(f"静默修正 #{attempt} 完成")

    # 最终验证
    try:
        parsed = json.loads(raw_output)
        valid, err = validate_json(parsed)
        if valid:
            logger.info("静默修正成功，结果符合 Schema")
        else:
            logger.error(f"静默修正后仍不符合 Schema: {err}")
    except json.JSONDecodeError as e:
        logger.error(f"静默修正后仍不是合法 JSON: {e}")
    
    return raw_output

@retry_sync(times=3, delay=2)
def generate_structured_with_retry(prompt: str):
    """
    静默生成符合 Schema 的 JSON，不产生任何输出
    """
    schema = load_schema()
    if schema is None:
        raise RuntimeError("JSON Schema 未加载")
    
    system_prompt = (
        "请基于用户输入生成符合 JSON Schema 的响应，仅输出 JSON，不要包含多余文本。"
        f"Schema: {json.dumps(schema, ensure_ascii=False)}"
    )
    
    # 重定向 stdout 确保完全静默
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    for attempt in range(1, 4):
        try:
            # 使用非流式调用
            resp = openai.chat.completions.create(
                model=os.getenv('LLM_MODEL', 'gpt-4'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            text = resp.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"第{attempt}次 LLM 调用异常: {e}")
            if attempt < 3:
                continue
            else:
                # 恢复 stdout 后退出
                sys.stdout = original_stdout
                raise
        
        try:
            obj = json.loads(text)
        except Exception:
            logging.warning(f"第{attempt}次输出非 JSON，需要仅输出 JSON 提示")
            system_prompt = "请仅输出有效 JSON，不要包含解释文字，仅返回 JSON 对象。Schema: " + json.dumps(schema, ensure_ascii=False)
            continue
        
        valid, err = validate_json(obj)
        if valid:
            # 恢复 stdout 后返回
            sys.stdout = original_stdout
            return json.dumps(obj, ensure_ascii=False)
        else:
            logging.warning(f"第{attempt}次输出不符合 Schema: {err}")
            system_prompt = f"前次输出不符合 Schema: {err}。请只输出符合 Schema 的 JSON。Schema: {json.dumps(schema, ensure_ascii=False)}"
            continue
    
    # 恢复 stdout
    sys.stdout = original_stdout
    # 最终返回空对象
    return json.dumps({}, ensure_ascii=False)