import argparse
import os
import json
import logging
import sys
import time
from modules.preprocessing import preprocess
from modules.llm_client import LLMClient
from modules.validator import validate_json, request_correction
from modules.multimodal import MultiModalProcessor
from modules.rag import RAGRetriever, augment_query_with_rag
from modules.memory_manager import MemoryManager
from modules.agent_extension import AdvancedAgent

# ANSI 颜色代码用于美化输出
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

logger = logging.getLogger(__name__)

def print_separator():
    """打印装饰性的分隔线"""
    print(f"{BLUE}{'-' * 50}{RESET}")

def run_cli():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Enhanced LLM Application CLI")
    parser.add_argument('--model', type=str, default='gpt-3.5-turbo', help='LLM model name')
    parser.add_argument('--temp', type=float, default=0.7, help='Temperature parameter')
    parser.add_argument('--top_p', type=float, default=1.0, help='Top_p parameter')
    parser.add_argument('--enable_multimodal', action='store_true', help='Enable multimodal input (image/audio)')
    parser.add_argument('--image_input', type=str, help='Image input path')
    parser.add_argument('--audio_input', type=str, help='Audio input path')
    parser.add_argument('--enable_rag', action='store_true', help='Enable RAG retrieval augmentation')
    parser.add_argument('--rag_index', type=str, help='RAG index prefix path')
    parser.add_argument('--rag_docs', type=str, help='RAG documents JSON file path')
    parser.add_argument('--enable_memory', action='store_true', help='Enable conversation history')
    parser.add_argument('--use_advanced_agent', action='store_true', help='Use custom AdvancedAgent')
    args = parser.parse_args()

    # 初始化组件
    llm = LLMClient(model_name=args.model)
    multimodal = MultiModalProcessor() if args.enable_multimodal else None

    rag = None
    if args.enable_rag:
        retriever = RAGRetriever(index_prefix=args.rag_index) if args.rag_index else RAGRetriever()
        if args.rag_docs and os.path.exists(args.rag_docs):
            with open(args.rag_docs, 'r', encoding='utf-8') as f:
                docs = json.load(f)
            retriever.build_index(docs)
        rag = retriever
    memory = MemoryManager() if args.enable_memory else None
    agent = AdvancedAgent(user_id='cli_user', rag=rag) if args.use_advanced_agent else None

    # 主交互循环
    print(f"{GREEN}Welcome to Enhanced LLM CLI! Type 'exit' to quit.{RESET}")
    while True:
        user_input = input(f"\n{YELLOW}Enter your request: {RESET}")
        if user_input.lower() in ('exit', 'quit'):
            print(f"{GREEN}Goodbye!{RESET}")
            break

        clean_input = preprocess(user_input)
        if not clean_input.strip():
            print(f"{YELLOW}Input is empty or filtered. Please try again.{RESET}")
            continue

        print_separator()

        # 多模态处理
        if multimodal:
            if args.image_input and os.path.exists(args.image_input):
                # 传递当前使用的模型
                desc = multimodal.process_image_input(args.image_input, model_name=args.model)
                print(f"{BLUE}[多模态] 图像描述:{RESET} {desc}")
                clean_input = f"图像描述: {desc}\n用户输入: {clean_input}"
            if args.audio_input and os.path.exists(args.audio_input):
                txt = multimodal.process_audio_input(args.audio_input)
                print(f"{BLUE}[多模态] 音频转录:{RESET} {txt}")
                clean_input = txt or clean_input

        # 代理模式
        if agent:
            print(f"{BLUE}[Agent] Processing...{RESET}")
            time.sleep(0.5)  # 模拟思考延迟
            try:
                response = agent.decide_and_execute(clean_input)
                print(response)  # 代理模式下直接输出响应
            except Exception as e:
                logger.error(f"Agent processing failed: {e}")
                print(f"{YELLOW}Error: Agent processing failed.{RESET}")
            print_separator()
            continue

        # RAG 模式
        prompt_to_use = clean_input
        if rag:
            retrieved = rag.retrieve(clean_input)
            if retrieved:
                print(f"{BLUE}[RAG] Retrieved References:{RESET}")
                for i, doc in enumerate(retrieved, 1):
                    print(f"{i}. {doc['content'][:100]}...")
                context = "\n".join([doc["content"] for doc in retrieved])
                prompt_to_use = augment_query_with_rag(clean_input, rag)
                print(f"{BLUE}[RAG] Augmented Query:{RESET} {prompt_to_use[:100]}...")
            else:
                print(f"{BLUE}[RAG] No relevant references found.{RESET}")

        # 记忆模式
        if memory:
            history = memory.get_history('cli_user', limit=5)
            if history:
                print(f"{BLUE}[Memory] Conversation History:{RESET}")
                for msg in history:
                    print(f"{msg['role']}: {msg['content'][:50]}...")
            memory.add_message('cli_user', 'user', clean_input)

        # LLM 响应生成
        print(f"{BLUE}[LLM] Generating response...{RESET}")
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Respond in JSON per schema.json."},
                {"role": "user", "content": prompt_to_use}
            ]
            if memory:
                history = memory.get_history('cli_user', limit=5)
                messages = [{"role": "system", "content": "You are a helpful assistant. Respond in JSON per schema.json."}] + history + [{"role": "user", "content": prompt_to_use}]
            response = llm.chat_stream(messages, temperature=args.temp, top_p=args.top_p)

            # JSON 验证和修正
            try:
                json_response = json.loads(response)
                valid, error = validate_json(json_response)
                if not valid:
                    # print(f"{YELLOW}Validation error: {error}{RESET}")
                    # corrected = request_correction(llm, response, clean_input)
                    # print(f"{BLUE}Corrected JSON:{RESET}")
                    # print(json.dumps(json.loads(corrected), ensure_ascii=False, indent=2))
                    logger.warning(f"JSON validation failed: {error}")
                    # 后台静默修正
                    corrected = request_correction(llm, response, clean_input)
                    logger.info(f"Corrected response: {corrected[:100]}...")
                # else:
                #     print(f"{BLUE}Valid JSON:{RESET}")
                #     print(json.dumps(json_response, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                # print(f"{YELLOW}Failed to parse response as JSON:{RESET}")
                # print(response)
                logger.error("Response is not valid JSON")

            # 添加到记忆
            if memory:
                memory.add_message('cli_user', 'assistant', response)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            print(f"{YELLOW}Error: LLM response generation failed.{RESET}")

        print_separator()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cli()