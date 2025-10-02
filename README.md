# SciAgent ⚙️

## Environment Setup 🧰

### Install SciAgent

Requires Python 3.10+.

```bash
conda create -n sciagent python=3.10 -y
conda activate sciagent
pip install -e .
```

### Run your first Sci-Agent
```bash
bash SciAgent/run_scripts/run.sh
```

### Setting API Key 🔑

All keys and Base_URL are stored in `.env`:

```bash
API_BASE=Base_URL
API_KEY=sk-XXXXXXXXXXXXXXXXXXXX
```

---

## Acknowledgments 🙏

[`smolagents`](https://github.com/huggingface/smolagents)

[`Physics-Supernova`](https://github.com/CharlesQ9/Physics-Supernova)
