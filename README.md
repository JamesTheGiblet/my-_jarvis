Self-Evolving AI System: Praxis

Built on Bio-Driven Backend Design (BDBD) A living codebase. An AI that grows.

🌐 Overview

Praxis is an experimental AI assistant project designed to be modular and intelligent, with a long-term vision of evolving over time. It draws inspiration from biological systems, aiming for an architecture that can adapt and grow.

While the ultimate goal is a system that monitors itself, learns from interactions, and dynamically refines its behaviors, the current version serves as a robust foundation. It leverages the Gemini API for advanced language understanding and a dynamic skill-loading mechanism for extensibility.

    🧬 The aspirational goal is for Praxis to reach a level of functional complexity where it can contribute to its own evolution, perhaps even naming itself.

🎯 Project Genesis & Motivation

The inspiration for Praxis stems from a desire to create a J.A.R.V.I.S.-like AI—a truly interactive and intelligent companion. Early explorations into "build your own J.A.R.V.I.S. in 10 steps" tutorials proved unsatisfying, often resulting in superficial programs reliant on limited, API-centric approaches without foundational depth.

This led to the development of Praxis, a ground-up endeavor built on a personal "bio-driven design" philosophy—an intuitive vision for how an intelligent, adaptive system should run and evolve. The current implementation, utilizing the Gemini API and a flexible skill system, is the first major step in realizing this vision.

A core tenet from the outset has been the AI's potential for true autonomy. Praxis is an attempt to build something more authentic, adaptable, and genuinely intelligent, starting with a strong, modular base.

🌟 Key Principles (Guiding Philosophy)

These principles guide the ongoing development and future aspirations of Praxis:

Principle          | Description
-------------------|----------------------------------------------------------------------------------------------------
Self-Actualization | The system aims to become increasingly autonomous, eventually optimizing its own structure and performance.
Bio-Inspired Modularity | Foundational skills and future modules are envisioned to behave like cells or organisms — evolving, merging, retiring, or replicating.
Emergent Intelligence | Complex behaviors are expected to emerge from the interaction of simpler, well-defined components and learning processes.
Context-Aware Execution | APIs and logic should adapt based on internal state and real-world usage context. The current `SkillContext` is a first step.
Iterative Evolution | Changes are not abrupt but grow from prior structures, much like biological mutation and selection.

🚀 Current Capabilities & Foundational Features

Praxis is continuously developing. Here are some of the key capabilities built upon its current Gemini API and skill-based architecture:

*   **Modular Skill Architecture:**
    *   Dynamically loads and integrates new capabilities (skills) from Python files at runtime (see `skills/How to create a skill.txt`).
    *   Skills are self-contained, promoting clean separation of concerns and easy extension.
    *   This forms the bedrock for future self-adaptive module generation.

*   **LLM-Powered Orchestration (Gemini API):**
    *   Utilizes Google's Gemini API for advanced natural language understanding, command interpretation, and conversational abilities.
    *   Intelligently selects appropriate skills and extracts necessary arguments to fulfill user requests, as managed in `brain.py`.
    *   Maintains conversation history (`chat_session`) for contextual understanding across multiple turns.

*   **Context-Aware Skill Execution:**
    *   Skills operate with a shared `SkillContext`, providing access to system functions (like `speak()`) and the ongoing conversation history.
    *   This lays the groundwork for more sophisticated contextual adaptations as Praxis evolves.

*   **Extensible Knowledge & Interaction:**
    *   The `chat_session` with the Gemini API provides immediate conversational memory.
    *   The system is designed to allow for the future integration of more persistent knowledge bases and advanced learning mechanisms.

*   **Developer-Friendly Skill Creation:**
    *   A clear process for adding new foundational skills, enabling rapid expansion of capabilities.
    *   Includes a self-test mechanism (`_test_skill`) within skill modules to help ensure integrity and successful integration.

🧩 Current Architecture Overview

Praxis's current architecture is designed for clarity and extensibility:

*   **Core Orchestration Layer:**
    *   `main.py`: The central orchestrator, managing the main interaction loop, user input/output, dynamic skill loading, and skill execution.
    *   `brain.py`: Interfaces with the Gemini API (`process_command_with_llm`) to understand user intent and determine the appropriate skill and arguments.
    *   `config.py`: Manages API keys and essential configurations for the Gemini API.

*   **Dynamic Skill Modules (`skills/` directory):**
    *   Individual `.py` files in this directory define one or more skills (Python functions).
    *   Skills are automatically discovered and made available to the LLM-driven `brain.py`.
    *   This modularity is inspired by biological principles, where each skill acts as a specialized functional unit.

*   **Interaction & Context (`SkillContext`):**
    *   Provides a standardized interface for skills to interact with the core system (e.g., for speech output via `speak()`) and access shared information like the conversation history.

🧪 Path to Evolution (Future Aspirations)

While the current system relies on human developers to add skills and refine prompts, the Praxis vision includes a methodology for greater autonomy:

*   **Iterative Refinement:** The system will continue to evolve through the addition of new foundational skills and improvements to the LLM interaction strategies.
*   **Performance Monitoring & Feedback Loops (Future):**
    *   Mechanisms to track skill success rates, identify inefficiencies, and gather user feedback will be crucial for guiding autonomous improvements.
*   **Experimental Adaptation & Generation (Future):**
    *   The long-term goal is for Praxis to experiment with variations of existing skills or even attempt to generate new, simple capabilities based on observed needs or patterns of failure.
    *   This could involve techniques like LLM-driven code generation, guided by performance metrics.
*   **Pattern Recognition & Learning (Future):**
    *   Praxis will aim to learn from the history of interactions—successful skill executions, failures, and user corrections—to enhance its decision-making, skill selection, and potentially its own structure.
*   **Self-Assessment & Optimization (Future):**
    *   The system will eventually incorporate self-assessment routines to identify areas for optimization, both at the micro (individual skill) and macro (overall workflow) levels.
