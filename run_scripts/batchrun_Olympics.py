import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path

# ----------------------------
# Paths
# ----------------------------
# 当前文件: SciAgent/run_scripts/batchrun_Olympics.py
# 仓库根目录: SciAgent/
REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = REPO_ROOT / "run.py"

# ----------------------------
# Configuration for batch execution
# ----------------------------
MAX_THREADS = 1  # Maximum number of concurrent threads
NUM_PER_QUESTION = 1  # number of runs per problem

ARGS_LIST = [
    *[{
        "manager_model": "openai/gemini-2.5-pro",
        "review_tool_model": "openai/gemini-2.5-pro",
        "image_tool_model": "openai/gemini-2.5-pro",
        "breakdown_tool_model": "openai/gemini-2.5-pro",
        "summarize_tool_model": "openai/gemini-2.5-pro",
        "manager_type": "CodeAgent",
        "tools_list": [
            "ask_image_expert",
            "finalize_part_answer",
            "ask_review_expert",
            "breakdown_question_expert",
            "smiles_verify_expert",
        ],
        # 这些路径按 REPO_ROOT 解析
        "input_markdown_file": "examples/Problems/IChO25/problem1/theory1.md",
        "output_file_position": f"output/IChO2025_test/Q1/Q1_0926_{idx}.md",
    } for idx in range(NUM_PER_QUESTION)],
]


def build_command(args_dict):
    """Build the argv list to run run.py with the given arguments."""
    cmd = [
        sys.executable,
        str(RUN_PY),
        "--input-markdown-file",
        args_dict["input_markdown_file"],
        "--manager-model",
        args_dict["manager_model"],
        "--breakdown-tool-model",
        args_dict["breakdown_tool_model"],
        "--image-tool-model",
        args_dict["image_tool_model"],
        "--review-tool-model",
        args_dict["review_tool_model"],
        "--summarize-tool-model",
        args_dict["summarize_tool_model"],
        "--tools-list",
        *args_dict["tools_list"],
    ]

    # Optional args
    if "managed_agents_list_model" in args_dict:
        cmd.extend(["--managed-agents-list-model", args_dict["managed_agents_list_model"]])
    if "manager_type" in args_dict:
        cmd.extend(["--manager-type", args_dict["manager_type"]])
    if "managed_agents_list" in args_dict:
        cmd.extend(["--managed-agents-list", *args_dict["managed_agents_list"]])

    return cmd


def run_single_task(args_dict):
    """Run a single task with the given arguments."""
    try:
        cmd = build_command(args_dict)
        out_path = REPO_ROOT / args_dict["output_file_position"]
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Starting task:")
        print(f"  manager_model  : {args_dict['manager_model']}")
        print(f"  workdir (cwd)  : {REPO_ROOT}")
        print(f"  output file    : {out_path}")

        # 直接以列表形式运行，捕获 stdout/stderr 到文件（更稳）
        with open(out_path, "w") as f:
            result = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False,
            )

        if result.returncode == 0:
            print(f"✓ Task completed: {args_dict['manager_model']}")
        else:
            print(f"✗ Task failed: {args_dict['manager_model']} (code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"✗ Exception in task {args_dict['manager_model']}: {e}")
        return False


def main():
    """Main function to run all tasks with multithreading."""
    print(f"🚀 Starting batch execution with {MAX_THREADS} concurrent threads")
    print(f"📋 Total tasks: {len(ARGS_LIST)}")

    start_time = time.time()

    # Use ThreadPoolExecutor for concurrent execution
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_args = {executor.submit(run_single_task, args_dict): args_dict for args_dict in ARGS_LIST}

        completed = 0
        successful = 0

        for future in as_completed(future_to_args):
            _ = future_to_args[future]
            completed += 1
            try:
                success = future.result()
                if success:
                    successful += 1
                print(f"📊 Progress: {completed}/{len(ARGS_LIST)} tasks completed")
            except Exception as e:
                print(f"❌ Task failed with exception: {e}")

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n🏁 Execution Summary:")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"✅ Successful: {successful}/{len(ARGS_LIST)}")
    print(f"❌ Failed: {len(ARGS_LIST) - successful}")
    print(f"⚡ Average time per task: {total_time/len(ARGS_LIST):.2f} seconds")


if __name__ == "__main__":
    main()
