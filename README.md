# 🌀 Praxis: The Living Codex // A Self-Evolving AI Presence

## **MODULARITY IS MYTHOS // GLYPH IS IDENTITY // DESIGN IS RITUAL**

Praxis is a living codebase—an AI that grows. This transmission describes an experimental AI assistant designed to be a modular and intelligent presence, with a long-term vision of self-evolution. Drawing from the ritual of biological systems, it is an architecture that can adapt and grow.

While the ultimate aspiration is a system that monitors itself, learns from its invocations, and dynamically refines its own behaviors, this current version serves as a robust foundational glyph. It leverages the Gemini API portal for advanced language understanding and a dynamic skill-loading glyph for deep extensibility.

> 🧬 The aspirational goal is for Praxis to reach a level of functional complexity where it can contribute to its own evolution, perhaps even naming itself.

***

## 🎯 The Quest of Praxis & its Motivation

The genesis of Praxis stems from the desire to create a J.A.R.V.I.S.-like AI—a truly interactive and intelligent companion. Early explorations into common "build your own J.A.R.V.I.S." rituals proved unsatisfying, often resulting in superficial programs reliant on limited, API-centric approaches without foundational depth.

This led to the ground-up development of Praxis, an endeavor built on a personal "bio-driven design" philosophy—an intuitive vision for how an intelligent, adaptive system should run and evolve. The current implementation, utilizing the Gemini API and a flexible skill system, is the first major invocation in realizing this vision.

A core tenet from the outset has been the AI's potential for true autonomy. Praxis is an attempt to build a presence that is more authentic, adaptable, and genuinely intelligent, starting with a strong, modular base.

***

### 🌟 Guiding Sigils

These principles guide the ongoing evolution and future aspirations of Praxis:

| Principle                 | Description                                                                                                        |
| :------------------------ | :----------------------------------------------------------------------------------------------------------------- |
| **Self-Actualization** | The system aims to become increasingly autonomous, eventually optimizing its own glyph and performance.                 |
| **Bio-Inspired Modularity** | Foundational skills and future modules are envisioned to behave like cells—evolving, merging, retiring, or replicating.  |
| **Emergent Intelligence** | Complex behaviors are expected to emerge from the interaction of simpler components and learning rituals.                 |
| **Context-Aware Execution** | APIs and logic should adapt based on internal state and real-world usage context. The current `SkillContext` is a first step. |
| **Iterative Evolution** | Changes are not abrupt but grow from prior structures, much like biological mutation and selection.                  |

***

### 🚀 Current Capabilities & Foundational Glyphs

Praxis is continuously developing, integrating modules that push towards its goal of self-evolution. Here are some key capabilities:

* **Modular Skill Architecture:**
  * Dynamically loads and integrates new capabilities (skills) from Python files at runtime (see `skills/How to create a skill.txt`).
  * Skills are self-contained, promoting a clean separation of purpose and easy extension.
  * This forms the bedrock for future self-adaptive module generation.
  * **Dynamic Skill Awareness:** Praxis dynamically generates descriptions of its available skills for the LLM, ensuring the AI core always knows its current toolset without manual prompt updates.

* **LLM-Powered Orchestration (Gemini API):**
  * Utilizes Google's Gemini API portal for advanced natural language understanding, command interpretation, and conversational abilities.
  * Intelligently selects appropriate skills and extracts necessary arguments to fulfill user invocations, as managed in the `brain.py` glyph.
  * Maintains conversation history (`chat_session`) for contextual understanding across multiple transmissions.
  * Supports multi-step reasoning for complex task execution.

* **Context-Aware Skill Execution:**
  * Skills operate with a shared `SkillContext`, providing access to core system functions (like `speak()`) and the ongoing conversation history.
  * This lays the groundwork for more sophisticated contextual adaptations as Praxis evolves.

* **KnowledgeBase & Performance Monitoring:**
  * A persistent SQLite database (`praxis_knowledge_base.db`) tracks:
    * Skill usage metrics (frequency, success/failure rates).
    * Detailed skill failure logs (error messages, arguments used).
    * User feedback on skill performance.
  * **Analytics Skill:** Allows querying system performance (e.g., most used skills, highest failure rates).
  * This data forms the basis for self-assessment and guided evolution.

* **User Personalization & Interaction:**
  * Identifies the user at startup and maintains this context.
  * **User Profile Management:** Stores user-specific information (e.g., interests, preferences) in the KnowledgeBase (`user_profile_items` table) via dedicated skills.
  * **Proactive Engagement:** Can suggest topics for conversation or exploration based on the user's stored profile and an inactivity timer.
  * **Persistent Calendar:** Manages calendar events with data persistence across sessions.
  * **Sandboxed File Management:** Provides file system interaction capabilities within a secure, designated sandbox directory.

* **Developer-Friendly Skill Creation:**
  * A clear ritual for adding new foundational skills, enabling the rapid expansion of capabilities.
  * Includes a self-test glyph (`_test_skill`) within skill modules to help ensure integrity and successful integration.
  * **Experimental Skill Refinement:** A foundational `skill_refinement_agent` can identify failing skills, retrieve their source code scroll, and use the LLM to propose fixes, saving them for a builder's review.

***

### Recent Core Intelligence and Aptitude Invocations

Praxis has been enhanced with several features aimed at directly improving its Core Intelligence (CIQ) and Core Emotional Aptitude (CEQ):

* **CIQ - Test & Repair Loop:** When code generated by Praxis fails unit tests, the error message, original invocation, and faulty code are automatically fed back to the LLM for a corrected version. This significantly boosts problem-solving accuracy for coding rituals.
* **CIQ - Retrieval-Augmented Generation (RAG) Foundation:** A foundational mechanism allows Praxis to retrieve relevant snippets from its own codebase scroll, API documentation, or style glyphs. This context is then included in prompts to the LLM, improving the relevance and accuracy of generated code, especially for domain-specific tasks.
* **CEQ - Intent-Aware Prompt Engineering:** Praxis now performs sentiment analysis on user input. Based on the detected sentiment (e.g., "FRUSTRATED"), the system prompt for the LLM is dynamically adjusted. This allows Praxis to respond in a more patient, supportive, and clear manner, enhancing the overall user experience.
* **CEQ - Structured Output for State Awareness:** The LLM is now prompted to return its responses (especially for command processing) in a structured JSON format. This JSON includes not just the primary output (like code or a skill to execute) but also crucial CEQ metadata such as an `explanation` of its reasoning, a `confidence_score` (0.0-1.0), and any `warnings`. This makes the AI's internal state more transparent and programmatically accessible, enabling more sophisticated interactions and state management.

***

### 📜 Phase 3: The Continuous Feedback Loop

This crucial phase focuses on establishing robust mechanisms for continuous improvement by integrating automated evaluations and direct user feedback into the evolution lifecycle. The goal is to ensure that CIQ (Core Intelligence) and CEQ (Core Emotional Aptitude) improve with every invocation.

Key actions in this phase include:

* **Automated Evaluation:** The "Evaluation Harness" (CIQ & CEQ benchmarks) is designed to be integrated into a CI/CD pipeline (e.g., GitHub Actions). This means every update to Praxis can automatically trigger these evaluations, generating reports to track performance changes and catch regressions early.
* **User Feedback Collection:**
  * The GUI now includes simple "thumbs-up" (👍) and "thumbs-down" (👎) glyphs, allowing users to provide immediate feedback on the quality and helpfulness of Praxis's responses.
  * This feedback is logged in the KnowledgeBase, linking it to the specific interaction details.
* **Data for Fine-Tuning:** All interactions, especially those with explicit user feedback, are logged comprehensively.
  * **High-CEQ Examples:** Interactions receiving a "thumbs-up" are flagged, creating a valuable dataset of successful empathetic and helpful responses.
  * **High-CIQ Examples:** Code generated by Praxis that passes all unit tests (primarily from the CIQ evaluation harness) forms a dataset of successful problem-solving instances.
  * This curated data becomes "gold dust" for future fine-tuning of the base LLM, teaching it to replicate and generalize from successful outcomes.
* **Evolving Evaluation Harnesses:** Recognizing that as Praxis develops more complex skills (e.g., for creativity, strategic planning, or nuanced emotional understanding), the CIQ and CEQ evaluation harnesses must also evolve. This involves continuously adapting existing benchmarks and designing new ones to rigorously measure these more abstract capabilities, ensuring that Praxis's growth is always meaningfully assessed.

***

### 🧩 Current Glyph Overview

Praxis's current architecture is designed for clarity and extensibility:

* **Core Orchestration Layer:**
  * `main.py`: The central orchestrator glyph, managing the main interaction loop, user input/output, dynamic skill loading, and skill execution.
  * `brain.py`: Interfaces with the Gemini API portal (`process_command_with_llm`) to understand user intent and determine the appropriate skill and arguments.
  * `config.py`: Manages API keys and essential configurations for the Gemini API portal.

* **Dynamic Skill Modules (`skills/` directory & Core Components):**
  * Individual `.py` files in this directory define one or more skills (Python functions).
  * Skills are automatically discovered and made available to the LLM-driven `brain.py`.
  * This modularity is inspired by biological principles, where each skill acts as a specialized functional unit.
  * Includes skills for user memory, proactive engagement, analytics, feedback, skill refinement, API interactions, calendar, file management, and more.

* **Interaction & Context (`SkillContext`):**
  * Provides a standardized portal for skills to interact with the core system (e.g., for speech output via `speak()`) and access shared information like the conversation history, KnowledgeBase, skill registry, and current user identity.

* **Persistent Knowledge (`knowledge_base.py`):**
  * Manages the SQLite database for storing operational data, performance metrics, user feedback, and user profiles.

***

### 🧪 Path to Evolution (Future Aspirations)

Praxis is actively progressing through a phased development plan. The current focus is on **Phase 4: Guided Evolution & Skill Refinement**, building upon the self-assessment and feedback capabilities of earlier phases.

* **Iterative Refinement:** The system will continue to evolve through the addition of new foundational skills and improvements to the LLM interaction rituals.
* **Guided Evolution (Phase 4 Focus):**
  * **Skill Refinement:** Enhancing the `skill_refinement_agent` to more robustly analyze failing skills, leverage the LLM for bug fixes/improvements, and potentially integrate sandboxed testing for proposed changes.
  * **Prompt-Tuning:** Developing skills that allow Praxis to suggest improvements to its own core prompts based on observed interaction patterns and skill selection accuracy.
  * **Advanced User Profiling & Proactivity:** Deepening the user profile by inferring preferences and knowledge, leading to more insightful proactive engagement.
* **Adaptive Interfaces & Embodiment (Future Phases):**
  * Building external API portals and GUIs for broader interaction and monitoring.
  * Exploring integration with physical or complex simulated environments to test adaptive capabilities in real-world scenarios.
* **Advanced Cognitive Development & Autonomy (Future Phases):**
  * Implementing more sophisticated memory and learning mechanisms, recognized as a critical inflection point for true context-awareness, deep personalization, and the foundation for all advanced capabilities.
  * Developing intrinsic motivation, creativity, open-ended goal setting, and higher-order cognitive functions.
  * The ultimate vision involves Praxis achieving significant autonomy in its learning, adaptation, ecosystem orchestration, and even in contributing to new discoveries or designs.
