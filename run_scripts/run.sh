python test/run.py \
  --input-markdown-file examples/Problems/IPhO25/problem_test/theory1.md \
  --manager-model openai/gemini-2.5-pro \
  --breakdown-tool-model openai/gemini-2.5-pro \
  --image-tool-model openai/gemini-2.5-pro \
  --review-tool-model openai/gemini-2.5-pro \
  --summarize-tool-model openai/gemini-2.5-pro \
  --manager-type SciCodeAgent \
  --tools-list ask_image_expert finalize_part_answer ask_review_expert breakdown_question_expert smiles_verify_expert \
  > "output/IPhO2025_test/Q1/Q1_0.md" 2>&1