# SciAgent: A Unified Multi-Agent System for Generalistic Scientific Reasoning

---

Official implementation of **SciAgent: A Unified Multi-Agent System for Generalistic Scientific Reasoning**

---

> **Abstract**: Recent advances in large language models have enabled AI systems to achieve expert-level performance on domain-specific scientific tasks, yet these systems remain narrow and handcrafted. We introduce SciAgent, a unified multi-agent system designed for generalistic scientific reasoning—the ability to adapt reasoning strategies across disciplines and difficulty levels. SciAgent organizes problem solving as a hierarchical process: a Coordinator Agent interprets each problem’s domain and complexity, dynamically orchestrating specialized Worker Systems, each composed of interacting reasoning Sub-agents for symbolic deduction, conceptual modeling, numerical computation, and verification. These agents collaboratively assemble and refine reasoning pipelines tailored to each task. This work establishes SciAgent as a concrete step toward generalistic scientific intelligence—AI systems capable of coherent, cross-disciplinary reasoning at expert levels.

## Overview

- **Conceptual contribution:** We introduce generalistic scientific reasoning as a new paradigm for AI in science, emphasizing adaptability across domains and modalities.

- **Architectural innovation:** We propose a Coordinator–Worker–Sub-agents hierarchy in which the Coordinator performs domain-adaptive routing and the Worker Systems self-assemble internal multi-agent pipelines.

- **Dynamic reasoning mechanism:** We demonstrate self-assembling, feedback-driven reasoning loops that integrate symbolic deduction, conceptual modeling, and quantitative computation.

| ![./assets/overview.png](./assets/overview.png) |
|:--:|
|SciAgent consists of a hierarchical multi-agent framework with a Coordinator Agent that routes problems to domain-specific Worker Systems. Each Worker System—Math, Physics, Chemistry, and General Exam—contains multiple Sub-agents (e.g., Generator, Reviewer, Image Analyser) collaborating through adaptive reasoning loops. The right panel summarizes key design principles: hierarchical meta-reasoning, modularity, and adaptive assembly.|

## TODO 🚀

All code releases will be made by November 20.

- [] Release the code of SciAgent framework.

- [] Release the code of Math Olympiad Worker System.

- [] Release the code of Physics Olympiad Worker System.

- [] Release the code of Chemistry Olympiad Worker System.

- [] Release the code of General Exam Worker System.


## Acknowledgement

This code is heavily inspired by [Somlagents](https://github.com/huggingface/smolagents), [IMO25](https://github.com/lyang36/IMO25), [Physics-Supernova](https://github.com/CharlesQ9/Physics-Supernova) and [SciToolAgent](https://github.com/HICAI-ZJU/SciToolAgent). Thank you for your outstanding work!


## License

This repository is licensed under the [Apache License Version 2.0](./LICENSE). You are free to use, modify, and distribute this code in compliance with the terms and conditions of the Apache License Version 2.0.
