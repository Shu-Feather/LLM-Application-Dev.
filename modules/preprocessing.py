import re
import os

# 加载敏感词列表
def load_sensitive_words(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

# 假设 project_root/test_data/sensitive_words.txt
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENSITIVE_WORDS = load_sensitive_words(os.path.join(BASE_DIR, 'test_data', 'sensitive_words.txt'))

def filter_sensitive(text: str) -> str:
    """
    简单替换敏感词为星号。实际项目可用更复杂策略。
    """
    if not SENSITIVE_WORDS:
        return text
    pattern = re.compile('|'.join(re.escape(w) for w in SENSITIVE_WORDS), flags=re.IGNORECASE)
    return pattern.sub(lambda m: '*' * len(m.group()), text)

def prevent_prompt_injection(user_input: str) -> str:
    """
    简单剥离可能的系统指令关键词，避免注入。
    """
    forbidden = ['system:', 'assistant:', 'role:']
    res = user_input
    for token in forbidden:
        # 如果检测到，移除该 token 及其后面可能的内容
        res = re.sub(fr'(?i){re.escape(token)}.*', '', res)
    return res.strip()

def preprocess(user_input: str) -> str:
    clean = filter_sensitive(user_input)
    clean = prevent_prompt_injection(clean)
    return clean
