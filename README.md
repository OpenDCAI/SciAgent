# 通用Agent System ⚙️

## 环境配置 🧰

### smolagent 📦

Requires Python 3.10+.

```bash
python -m pip install -U pip
pip install tenacity
pip install smolagents
pip install smolagents[litellm]
pip install loguru
pip install python-dotenv
```

### RAG system 📦

```bash 
pip install langchain
pip install langchain-core
pip install langchain-community
pip install langchain-openai
pip install chromadb
pip install langchain-chroma
pip install sentence-transformers
pip install python-dotenv
```
---

### 设置API Key 🔑

所有Key及Base_URL保存在 `.env` 中：

```bash
# 用于 Gemini 模型调用
OPENROUTER_API_BASE=Base_URL
OPENROUTER_API_KEY=sk-XXXXXXXXXXXXXXXXXXXX
```

---

## 文件结构 🗂️

```txt
SciAgent/
├── .env                            # API key
├── run.py                          # 主入口
├── run_scripts/
│   └── batchrun_Olympics.py        # 批处理 debug & evaluation for IPhO
├── utils/
│   ├── imgTools.py                 # 图像分析工具
│   ├── breakdownTools.py           # 问题分解工具
│   ├── rag_system.py               # RAG base系统
│   ├── data                        # RAG数据
│   ├── reviewTools.py              # solution审查工具
│   ├── smilesTools.py              # SMILEs验证工具
│   ├── summemoryTools.py           # 记忆总结工具
│   └── markdown_utils.py			# markdown处理
...
```

---

# 运行 🚀

### 批量执行 🧵

Edit and run `run_scripts/batchrun_Olympics.py`:

```python
MAX_THREADS = 1
NUM_PER_QUESTION = 1
ARGS_LIST = [
    *[{
        "manager_model":
        "openai/gemini-2.5-pro",
        "review_tool_model":
        "openai/gemini-2.5-pro",
        "image_tool_model":
        "openai/gemini-2.5-pro",
        "breakdown_tool_model":
        "openai/gemini-2.5-pro",
        "summarize_tool_model":
        "openai/gemini-2.5-pro",
        "manager_type":
        "CodeAgent",
        "tools_list": [
            "ask_image_expert",
            "finalize_part_answer",
            "ask_review_expert",
            "breakdown_question_expert",
            "smiles_verify_expert",
        ],
        "input_markdown_file":
        "examples/Problems/IChO25/problem1/theory1.md",
        "output_file_position":
        f"output/IChO2025_test/Q1/Q1_0926_{idx}.md",
    } for idx in range(NUM_PER_QUESTION)],
]
```
