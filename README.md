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

Praxis is continuously developing, integrating features that push towards its goal of self-evolution. Here are some key capabilities:

*   **Modular Skill Architecture:**
    *   Dynamically loads and integrates new capabilities (skills) from Python files at runtime (see `skills/How to create a skill.txt`).
    *   Skills are self-contained, promoting clean separation of concerns and easy extension.
    *   This forms the bedrock for future self-adaptive module generation.
    *   **Dynamic Skill Awareness:** Praxis dynamically generates descriptions of its available skills for the LLM, ensuring the AI core always knows its current toolset without manual prompt updates.

*   **LLM-Powered Orchestration (Gemini API):**
    *   Utilizes Google's Gemini API for advanced natural language understanding, command interpretation, and conversational abilities.
    *   Intelligently selects appropriate skills and extracts necessary arguments to fulfill user requests, as managed in `brain.py`.
    *   Maintains conversation history (`chat_session`) for contextual understanding across multiple turns.
    *   Supports multi-step reasoning for complex task execution.

*   **Context-Aware Skill Execution:**
    *   Skills operate with a shared `SkillContext`, providing access to system functions (like `speak()`) and the ongoing conversation history.
    *   This lays the groundwork for more sophisticated contextual adaptations as Praxis evolves.

*   **KnowledgeBase & Performance Monitoring:**
    *   A persistent SQLite database (`praxis_knowledge_base.db`) tracks:
        *   Skill usage metrics (frequency, success/failure rates).
        *   Detailed skill failure logs (error messages, arguments used).
        *   User feedback on skill performance.
    *   **Analytics Skill:** Allows querying system performance (e.g., most used skills, highest failure rates).
    *   This data forms the basis for self-assessment and guided evolution.

*   **User Personalization & Interaction:**
    *   Identifies the user at startup and maintains this context.
    *   **User Profile Management:** Stores user-specific information (e.g., interests, preferences) in the KnowledgeBase (`user_profile_items` table) via dedicated skills.
    *   **Proactive Engagement:** Can suggest topics for conversation or exploration based on the user's stored profile and an inactivity timer.
    *   **Persistent Calendar:** Manages calendar events with data persistence across sessions.
    *   **Sandboxed File Management:** Provides file system interaction capabilities within a secure, designated sandbox directory.

*   **Developer-Friendly Skill Creation:**
    *   A clear process for adding new foundational skills, enabling rapid expansion of capabilities.
    *   Includes a self-test mechanism (`_test_skill`) within skill modules to help ensure integrity and successful integration.
    *   **Experimental Skill Refinement:** A foundational `skill_refinement_agent` can identify failing skills, retrieve their source code, and use the LLM to propose fixes, saving them for developer review.

## Recent Core Intelligence and Aptitude Enhancements

Praxis has been enhanced with several features aimed at directly improving its Intelligence (CIQ) and Emotional Aptitude (CEQ):

*   **CIQ - Test & Repair Loop:** When code generated by Praxis fails unit tests, the error message, original prompt, and faulty code are automatically fed back to the LLM for a corrected version. This significantly boosts problem-solving accuracy for coding tasks.
*   **CIQ - Retrieval-Augmented Generation (RAG) Foundation:** A foundational mechanism allows Praxis to retrieve relevant snippets from its own codebase, API documentation, or style guides. This context is then included in prompts to the LLM, improving the relevance and accuracy of generated code, especially for domain-specific tasks. (Initial placeholder implemented).
*   **CEQ - Intent-Aware Prompt Engineering:** Praxis now performs sentiment analysis on user input. Based on the detected sentiment (e.g., "FRUSTRATED"), the system prompt for the LLM is dynamically adjusted. This allows Praxis to respond in a more patient, supportive, and clear manner, enhancing the overall user experience.
*   **CEQ - Structured Output for State Awareness:** The LLM is now prompted to return its responses (especially for command processing) in a structured JSON format. This JSON includes not just the primary output (like code or a skill to execute) but also crucial CEQ metadata such as an `explanation` of its reasoning, a `confidence_score` (0.0-1.0), and any `warnings`. This makes the AI's internal state more transparent and programmatically accessible, enabling more sophisticated interactions and state management.

---

🧩 Current Architecture Overview

Praxis's current architecture is designed for clarity and extensibility:

*   **Core Orchestration Layer:**
    *   `main.py`: The central orchestrator, managing the main interaction loop, user input/output, dynamic skill loading, and skill execution.
    *   `brain.py`: Interfaces with the Gemini API (`process_command_with_llm`) to understand user intent and determine the appropriate skill and arguments.
    *   `config.py`: Manages API keys and essential configurations for the Gemini API.

*   **Dynamic Skill Modules (`skills/` directory & Core Components):**
    *   Individual `.py` files in this directory define one or more skills (Python functions).
    *   Skills are automatically discovered and made available to the LLM-driven `brain.py`.
    *   This modularity is inspired by biological principles, where each skill acts as a specialized functional unit.
    *   Includes skills for user memory, proactive engagement, analytics, feedback, skill refinement, API interactions, calendar, file management, and more.

*   **Interaction & Context (`SkillContext`):**
    *   Provides a standardized interface for skills to interact with the core system (e.g., for speech output via `speak()`) and access shared information like the conversation history, KnowledgeBase, skill registry, and current user identity.

*   **Persistent Knowledge (`knowledge_base.py`):**
    *   Manages the SQLite database for storing operational data, performance metrics, user feedback, and user profiles.

🧪 Path to Evolution (Future Aspirations)

Praxis is actively progressing through a phased development plan. The current focus is on **Phase 3: Guided Evolution & Skill Refinement**, building upon the self-assessment capabilities of Phase 2.

*   **Iterative Refinement:** The system will continue to evolve through the addition of new foundational skills and improvements to the LLM interaction strategies.
*   **Guided Evolution (Phase 3 Focus):**
    *   **Skill Refinement:** Enhancing the `skill_refinement_agent` to more robustly analyze failing skills, leverage LLM for bug fixes/improvements, and potentially integrate sandboxed testing for proposed changes.
    *   **Prompt-Tuning:** Developing skills that allow Praxis to suggest improvements to its own core prompts based on observed interaction patterns and skill selection accuracy.
    *   **Advanced User Profiling & Proactivity:** Deepening the user profile by inferring preferences and knowledge, leading to more insightful proactive engagement.
*   **Adaptive Interfaces & Embodiment (Phases 4 & 8):**
    *   Building external APIs and GUIs for broader interaction and monitoring.
    *   Exploring integration with physical or complex simulated environments, including voice I/O, to test adaptive capabilities in real-world scenarios.
*   **Advanced Cognitive Development & Autonomy (Phases 5, 7, 9, 10):**
    *   Implementing more sophisticated memory and learning mechanisms, intrinsic motivation, creativity, open-ended goal setting, and higher-order cognitive functions.
    *   The ultimate vision involves Praxis achieving significant autonomy in its learning, adaptation, and even in contributing to new discoveries or designs.
