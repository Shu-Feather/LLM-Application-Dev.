# 多模态大语言模型应用基础层

本项目演示了一个基于 OpenAI 大语言模型（LLM）和可选 CAMEL-AI Agent 集成的基础功能层实现，涵盖环境配置、API 调用、流式响应、输入预处理、JSON Schema 校验与自动修正、CLI 交互示例等模块化设计。可作为进阶多模态、RAG、工具调用、Agent 自动化等功能的基石。

---

## 功能特性

- **环境与凭证管理**  
  - 通过 `.env` 加载 `OPENAI_API_KEY`，安全管理 API 密钥。  
- **输入预处理**  
  - 敏感词过滤：从 `test_data/sensitive_words.txt` 加载列表并替换。  
  - 提示注入防护：剥离常见系统指令关键词，避免用户注入恶意提示。  
- **LLM 调用**  
  - 使用 OpenAI Python SDK v1 (`openai.chat.completions.create`)，支持流式响应（打字机效果）和一次性调用。  
  - 参数调优演示：可对比不同 `temperature`（如 0.7 vs 1.2）对输出的影响。  
  - 异常重试：使用 `tenacity` 进行重试，提升调用稳定性。  
- **JSON Schema 校验与自动修正**  
  - 从项目根的 `config/schema.json` 加载预定义输出格式 Schema，使用 `jsonschema` 校验。  
  - 自动修正机制：当首次输出不符合 Schema 时，结合用户输入上下文及当前 UTC 时间，多次向 LLM 发送修正提示，引导其输出合法且有意义的 JSON。可在本地对常见结构（如将 dict 转数组）做轻量转换以减少修正次数。  
- **CLI 交互界面**  
  - 基于 `argparse`，支持指定模型名称、`temperature`、`top_p`，以及对比模式 (`--compare`)、CAMEL Agent 模式 (`--use_agent`)。  
  - 交互流程：读取用户输入，预处理后发起流式请求，实时打印并校验。  
  - 对空输入做预检并提示，减少无效请求。  
- **可选 CAMEL-AI Agent 集成**  
  - 如集成 `modules/agent_wrapper.py` 并安装 `camel-ai[all]`，可通过 `--use_agent` 调用 ChatAgent，支持多步对话与工具调用。  
  - 在需要结构化输出时，可结合 Schema 校验流程或二次提示。  
- **日志与异常处理**  
  - 使用 Python `logging` 记录关键流程（Schema 加载、API 调用、校验异常等）。  
  - `tenacity` 重试支持，捕获并日志记录失败详情。  
- **模块化与可扩展性**  
  - 各功能分离：`utils`、`preprocessing`、`llm_client`、`validator`、`interface` 等模块，便于维护与扩展。  
  - 可进一步扩展多模态处理、RAG 检索、记忆管理、外部工具（计算器、数据库、API、Python 解释器等）集成、Web/GUI 界面等。  
- **测试支持**  
  - `test_data/sample_inputs.json` 用于批量测试示例 Prompt；`sensitive_words.txt` 用于验证过滤逻辑。  
- **当前时间处理**  
  - 在提示中提供当前 UTC 时间示例，保证 `metadata.generated_at` 准确。  

---

## 依赖与环境

- **Python 版本**：3.10、3.11 或 3.12（与 CAMEL-AI 要求一致）。  
- **Conda 环境建议**：  
  ```bash
  conda create -n ai_project python=3.10 -y
  conda activate ai_project
  ```  
- **依赖列表 (`requirements.txt`)**：  
  ```text
  openai>=1.45.0,<2.0.0
  python-dotenv>=0.21.0
  jsonschema>=4.0.0
  tenacity>=8.0.0
  camel-ai[all]>=0.2.68

  # 如需 RAG:
  # sentence-transformers>=2.2.2
  # faiss-cpu>=1.7.3

  # 如需语音/Whisper:
  # openai-whisper>=20230314

  # 如需 Web 界面:
  # streamlit>=1.20.0
  # gradio>=3.0

  # 日志增强:
  # rich>=12.0.0

  # CLI 工具:
  # click>=8.0.0
  ```  
- **安装**：在激活环境后执行：  
  ```bash
  pip install -r requirements.txt
  ```  
- **API Key**：在项目根创建 `.env`，填写：  
  ```
  OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
  ```

---

## 代码结构

```
project_root/
├── .env
├── requirements.txt
├── README.md
├── main.py
├── modules/
│   ├── utils.py            # 重试装饰器与日志工具
│   ├── preprocessing.py    # 敏感词过滤与提示注入防护
│   ├── llm_client.py       # OpenAI SDK v1 调用：流式 & 一次性
│   ├── validator.py        # JSON Schema 加载、校验与自动修正
│   ├── interface.py        # CLI 交互逻辑
│   └── agent_wrapper.py    # 可选：CAMEL-AI ChatAgent 封装
├── config/
│   └── schema.json         # 输出 JSON Schema，自定义字段与格式
└── test_data/
    ├── sample_inputs.json  # 示例 Prompt 列表
    └── sensitive_words.txt # 敏感词列表
```

- **main.py**：入口，仅调用 `run_cli()` 并设置日志级别。  
- **modules/utils.py**：`retry_on_exception` 装饰器，基于 `tenacity`。  
- **modules/preprocessing.py**：加载并应用敏感词过滤及简单注入防护。  
- **modules/llm_client.py**：使用 `openai.chat.completions.create`（v1 接口）实现 `chat_stream`（流式）与 `chat_once`；提供 `compare_temperature` 方法演示参数调优。  
- **modules/validator.py**：基于 `jsonschema` 加载 `config/schema.json`，提供 `validate_json` 与 `request_correction`；提示中包含用户输入上下文和当前 UTC 时间，引导 LLM 生成符合 Schema 的有意义内容，并可本地轻量调整常见结构。  
- **modules/interface.py**：CLI：解析命令行参数 (`--model`, `--temp`, `--top_p`, `--compare`, `--use_agent`)，主循环读取用户输入、预处理、调用 LLM 或 Agent，打印流式输出并进行校验/修正，最后展示或保存结果。  
- **modules/agent_wrapper.py**（可选）：封装 CAMEL-AI `ChatAgent`，用于多步对话与工具调用，需安装 `camel-ai[all]` 并参考官方文档。  
- **config/schema.json**：定义输出格式字段，如 `summary`、`details`（数组形式，元素含 `title`/`content`）、`metadata`（包含 `generated_at`, `confidence`）。  
- **test_data/**：测试数据，用于快速验证项目功能。

---

## 安装与配置

1. **克隆或复制项目**：  
   ```bash
   git clone <repo_url>
   cd project_root
   ```  
2. **创建并激活 Conda 环境**：  
   ```bash
   conda create -n ai_project python=3.10 -y
   conda activate ai_project
   ```  
3. **安装依赖**：  
   ```bash
   pip install -r requirements.txt
   ```  
4. **配置 API Key**：在项目根创建 `.env`，加入：  
   ```
   OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
   ```  
5. **检查 Schema**：编辑 `config/schema.json`，确保其为合法 JSON 且字段符合预期。可使用 `jq . config/schema.json` 验证。  
6. **检查敏感词列表**：在 `test_data/sensitive_words.txt` 填写需要过滤的词汇。  

---

## 使用指南

### 基础功能层
1. 参数对比:
   ```bash
      # 参数对比测试
      python -c "from modules.compare import compare_params; compare_params('地壳中含量最高的五种元素是什么？')"
   ```

2. 基础交互界面(CLI):
   ```bash
     # 启动命令行界面
      python main.py --model gpt-4 --temp 0.7
   ```
3. 真实场景测试数据:
   ```bash
      python scripts/batch_test.py
   ```
4. 多模态扩展:
   ```bash
     # 图像描述生成
     python main.py --enable_multimodal --image_input <path/to/image.jpg>
   ```
5. 记忆机制:
   ```bash
      # 启用记忆功能
      python main.py --enable_memory
   ```
6. 外部工具集成:
   ```bash
      # 测试计算器工具
      python -c "from modules.tool_integration import CalculatorTool; print(CalculatorTool().eval_expr('2^3 + 5*2'))"
   ```

7. 自主Agent实现:
   ```bash
      # 启动Agent模式
      python main.py --use_advanced_agent
   ```

---

## 配置与扩展

- **修改 Schema**：编辑 `config/schema.json`，定义所需字段、类型、格式。CLI 与校验流程自动适配。  
- **扩展多模态**：可集成图像或语音处理模块，结合 OpenAI VLM 或 Whisper，将多模态输入转换为文本特征，传入 LLM。  
- **RAG 知识库**：使用 `sentence-transformers` + FAISS 构建本地向量库，或云服务，集成检索模块增强回答准确性。  
- **记忆管理**：持久化对话历史或用户画像，加载到提示中，实现长期记忆。  
- **工具调用**：结合 CAMEL-AI 或自建 FunctionTool，注册计算器、数据库查询、API 调用、代码执行等工具，支持 Agent 决策调用。  
- **Web/GUI 界面**：使用 Streamlit/Gradio 实现更友好的多模态上传、流式展示、可视化结果等。  
- **部署**：可容器化（Docker），部署到云或本地服务器，或打包为桌面应用。  

---

## 调试与常见问题

- **OpenAI SDK 版本**  
  - 已使用新版 v1 接口；确保 `openai>=1.45.0,<2.0.0`，否则可能出现 `APIRemovedInV1` 错误。  
  - 如需迁移旧代码，可参考迁移指南，使用 `openai migrate` 自动转换。  
- **CAMEL-AI 版本**  
  - 安装 `camel-ai[all]>=0.2.68`，支持 Python 3.10–3.12。参考官网安装指导。  
- **Schema 加载失败**  
  - 检查 `config/schema.json` 路径和文件内容；确保工作目录为项目根，且文件为合法 JSON。  
  - 日志会显示加载路径与错误，可根据提示修改路径或修复 JSON 格式。  
- **流式输出不连续**  
  - CLI 终端兼容性：在某些终端可能缓冲不同，可切换到常见终端或调整刷新逻辑。  
- **第一次输出不符合 Schema**  
  - 优化 `system_prompt`：在提示中明确字段结构（如 `details` 必须为数组、提供当前时间示例等），减少修正调用。  
  - 可本地预处理常见结构错误（如将 dict->array）。  
- **网络或 API 调用失败**  
  - `tenacity` 重试机制自动处理短暂故障；若持续失败，检查网络或 API Key 限制。  
- **敏感词过滤或注入防护过严**  
  - 根据需求调整 `test_data/sensitive_words.txt`，完善或放宽规则。  

---

## 参考文档

- **OpenAI Python SDK v1 迁移指南**：  
  - https://github.com/openai/openai-python/discussions/742  
- **CAMEL-AI 官方文档**：  
  - 安装与入门：支持 Python 3.10–3.12，快速搭建 Agent 与工具集成。  
  - 核心模块：Agents、工具、Loaders、Interpreters、RAG、Memory 等。  
- **JSON Schema 文档**：  
  - https://json-schema.org/  
- **tenacity 文档**：  
  - https://tenacity.readthedocs.io/  

---

## 许可证 & 贡献

- 本项目示例代码可根据课程或个人需求自由修改，无特定许可证限制；若与他人共享，请注明来源与改动。  
- 若希望贡献或扩展：可在 GitHub 仓库中提交 Issue 或 Pull Request，说明新增功能或优化点。  
