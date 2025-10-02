# Science Agent System ⚙️

## Environment Setup 🧰

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

### Setting API Key 🔑

All keys and Base_URL are stored in `.env`:

```bash
API_BASE=Base_URL
API_KEY=sk-XXXXXXXXXXXXXXXXXXXX
```

---

## File Structure 🗂️

```txt
SciAgent/
├── .env                            # API key
├── run.py                          # main entry point
├── run_scripts/
│   └── batchrun_science.py        # batch debugging & evaluation
├── sciagent/
│   ├── scicodeagent.py
│   └── scimonitoring.py
├── tools/
│   ├── imgTools.py                 # image analysis tools
│   ├── breakdownTools.py           # problem decomposition tools
│   ├── rag_system.py               # RAG base system
│   ├── data                        # RAG data
│   ├── reviewTools.py              # solution review tools
│   ├── smilesTools.py              # SMILES validation tools
│   ├── summemoryTools.py           # memory summarization tools
├── utils/
│   └── markdown_utils.py           # markdown processing
...
```

---

# Running 🚀

### Batch Execution 🧵

Edit and run `run_scripts/batchrun_science.py`:

```python
MAX_THREADS = 1
NUM_PER_QUESTION = 1
ARGS_LIST = [
    *[{
        "manager_model":
        "model_id",
        "review_tool_model":
        "model_id",
        "image_tool_model":
        "model_id",
        "breakdown_tool_model":
        "model_id",
        "summarize_tool_model":
        "model_id",
        "manager_type":
        "SciCodeAgent",
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
        f"output/IChO2025_test/Q1/Q1_{idx}.md",
    } for idx in range(NUM_PER_QUESTION)],
]
```

---

## Acknowledgments 🙏

[`smolagents`](https://github.com/huggingface/smolagents)

[`Physics-Supernova`](https://github.com/CharlesQ9/Physics-Supernova)
