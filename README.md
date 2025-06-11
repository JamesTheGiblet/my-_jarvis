Self-Evolving AI System: Praxis

Built on Bio-Driven Backend Design (BDBD) A living codebase. An AI that grows.

🌐 Overview

Praxis is an experimental AI assistant project designed to be modular and intelligent, with a long-term vision of evolving over time. It draws inspiration from biological systems, aiming for an architecture that can adapt and grow.

While the ultimate goal is a system that monitors itself, learns from interactions, and dynamically refines its behaviors, the current version serves as a robust foundation. It leverages the Gemini API for advanced language understanding and a dynamic skill-loading mechanism for extensibility.

    🧬 The aspirational goal is for Praxis to reach a level of functional complexity where it can contribute to its own evolution, perhaps even naming itself.

🎯 Project Praxis's Mission & Motivation

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

## Phase 3: The Continuous Feedback Loop

This crucial phase focuses on establishing robust mechanisms for continuous improvement by integrating automated evaluations and direct user feedback into the development lifecycle. The goal is to ensure that CIQ (Core Intelligence) and CEQ (Core Emotional Aptitude) improve with every iteration.

Key actions in this phase include:

*   **Automated Evaluation:** The "Evaluation Harness" (CIQ & CEQ benchmarks) is designed to be integrated into a CI/CD pipeline (e.g., GitHub Actions). This means every update to Praxis can automatically trigger these evaluations, generating reports to track performance changes and catch regressions early.
*   **User Feedback Collection:**
    *   The GUI now includes simple "thumbs-up" (👍) and "thumbs-down" (👎) buttons, allowing users to provide immediate feedback on the quality and helpfulness of Praxis's responses.
    *   This feedback is logged in the KnowledgeBase, linking it to the specific interaction details.
*   **Data for Fine-Tuning:** All interactions, especially those with explicit user feedback, are logged comprehensively.
    *   **High-CEQ Examples:** Interactions receiving a "thumbs-up" are flagged, creating a valuable dataset of successful empathetic and helpful responses.
    *   **High-CIQ Examples:** Code generated by Praxis that passes all unit tests (primarily from the CIQ evaluation harness) forms a dataset of successful problem-solving instances.
    *   This curated data becomes "gold dust" for future fine-tuning of the base LLM, teaching it to replicate and generalize from successful outcomes.
---

🧩 Current Architecture Overview (Corresponds to Phase 4+ in Plan of Action)

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

## Key Dependencies

Praxis relies on several key external libraries. Some of the most important ones include:

*   **Google Gemini API (`google-generativeai`)**: Powers the core language understanding, reasoning, and conversational capabilities. (Details in "LLM-Powered Orchestration").
*   **feedparser**: Essential for the news fetching skill, allowing Praxis to parse RSS and Atom feeds to retrieve news headlines.
    *   To install:
        ```bash
        pip install feedparser
        ```
*   **pyttsx3**: Used for Text-to-Speech (TTS) output, enabling Praxis to speak its responses.
*   **SpeechRecognition**: Leveraged for Speech-to-Text (STT) input, allowing Praxis to understand voice commands.

This list can be expanded as more core dependencies are integrated.

🧪 Path to Evolution (Future Aspirations)

Praxis is actively progressing through a phased development plan. The current focus is on **Phase 4: Guided Evolution & Skill Refinement** (see `plan_of_action.ini`), building upon the self-assessment and feedback capabilities of earlier phases.

*   **Iterative Refinement:** The system will continue to evolve through the addition of new foundational skills and improvements to the LLM interaction strategies.
*   **Guided Evolution (Phase 4 Focus):**
    *   **Skill Refinement:** Enhancing the `skill_refinement_agent` to more robustly analyze failing skills, leverage LLM for bug fixes/improvements, and potentially integrate sandboxed testing for proposed changes.
    *   **Prompt-Tuning:** Developing skills that allow Praxis to suggest improvements to its own core prompts based on observed interaction patterns and skill selection accuracy.
    *   **Advanced User Profiling & Proactivity:** Deepening the user profile by inferring preferences and knowledge, leading to more insightful proactive engagement.
*   **Adaptive Interfaces & Embodiment (Phases 4 & 8):**
    *   Building external APIs and GUIs for broader interaction and monitoring.
    *   Exploring integration with physical or complex simulated environments, including voice I/O, to test adaptive capabilities in real-world scenarios.
*   **Advanced Cognitive Development & Autonomy (Phases 5, 7, 9, 10):**
    *   Implementing more sophisticated memory and learning mechanisms, intrinsic motivation, creativity, open-ended goal setting, and higher-order cognitive functions.
    *   The ultimate vision involves Praxis achieving significant autonomy in its learning, adaptation, and even in contributing to new discoveries or designs.

### Enhanced Self-Awareness & Metacognition (Future Aspirations)

These skills would deepen Praxis's understanding of its own performance and learning process, accelerating its path to autonomy.

*   **Cognitive Resource Manager Skill:**
    *   **Concept:** A skill that monitors its own operational metrics. It would use `knowledge_base.py` to track API costs (e.g., token usage per call, cumulative costs), skill execution times, and potentially system memory usage if feasible.
    *   **Why it's valuable:** If it detects that a certain skill or type of operation is becoming too expensive (API cost-wise) or too slow, it could proactively:
        *   Log detailed warnings for developer review.
        *   Suggest optimizations to the relevant skill's code (leveraging the `skill_refinement_agent`).
        *   Temporarily adjust its strategy, perhaps by favoring less resource-intensive alternative skills if available.
        *   In extreme cases, and with safeguards, it might even temporarily disable a problematic, non-critical skill.
        This is a critical step for long-term, sustainable, and unmonitored operation, especially when relying on metered APIs.

*   **Automated Benchmark Generation Skill:**
    *   **Concept:** A true meta-skill. When a skill like `skill_refinement_agent` (or a future `autonomous_learning_agent`) successfully proposes or generates a new skill or a significant modification to an existing one, this "Automated Benchmark Generation Skill" would be tasked with analyzing the new/modified skill's code and docstrings. Based on this analysis, it would attempt to automatically write one or more basic unit tests for it and add them to the appropriate directory within an evaluation harness (e.g., `tests/skills/`).
    *   **Why it's valuable:** This would significantly close the loop on autonomous learning and self-improvement. Praxis wouldn't just be able to learn or modify skills; it would be able to generate evidence that its new or modified capabilities function as intended, ensuring that its evolution is robust, reliable, and less prone to regressions. It promotes a "test-driven evolution" paradigm.

### Deeper User Understanding & Personalization (Future Aspirations)

These skills would move Praxis from being a helpful assistant to a truly personalized companion that understands the user on a deeper level.

*   **Communication Style Adapter Skill:**
    *   **Concept:** An evolution of the CEQ (Core Emotional Aptitude) capabilities. This skill would analyze the user's language over time—noting their formality, verbosity, use of slang, emojis, and overall tone from interaction logs (`interaction_feedback` table in `knowledge_base.py`).
    *   **Why it's valuable:** Praxis could then dynamically tune its own responses (e.g., conciseness, descriptiveness, formality, even vocabulary choices by adjusting LLM prompts) to better match the user's preferred communication style. This would lead to more natural, comfortable, and effective interactions, making Praxis feel more like a tailored companion.

*   **Implicit Goal Inference Skill:**
    *   **Concept:** A skill that analyzes the history of user commands and interactions stored in the `knowledge_base.py` (specifically `skill_usage_metrics` and `interaction_feedback`) to identify patterns, recurring sequences of actions, or larger, unstated goals.
    *   **Why it's valuable:** This allows Praxis to be more proactive and insightful. For example, if a user frequently performs a sequence of file operations within a specific project directory and then runs tests, Praxis could proactively ask, "I've noticed you often test files after modifying them in this project. Would you like me to create a new skill that automatically runs the tests for you whenever a file in this directory changes?" This moves beyond simple command execution to anticipating user needs and offering intelligent assistance.

### Broader World Interaction & Knowledge Acquisition (Future Aspirations)

These skills would allow Praxis to break free from pre-defined APIs and learn directly from the vast, unstructured information on the internet.

*   **Web Scraper & Information Synthesizer Skill:**
    *   **Concept:** A skill that can take a URL, scrape the text content of the page (respecting `robots.txt` and ethical considerations), and then use the Gemini API to summarize the key points, extract specific information, or find the answer to a user's question based on that content.
    *   **Why it's valuable:** This would grant Praxis the ability to answer questions about current events, niche topics, or specific documentation pages that are not available through a structured API or its existing skills. It's a massive step towards general knowledge acquisition and a more versatile research assistant. It would likely require libraries like `requests` and `BeautifulSoup4` or `Scrapy`.

*   **RSS Feed & News Monitoring Skill:**
    *   **Concept:** An advanced version of the current news fetching (which uses `feedparser`). Users could task Praxis with monitoring specific RSS feeds or news sources for keywords, topics, or entities. When relevant new items are detected, Praxis could summarize them or alert the user.
    *   **Why it's valuable:** This would significantly enhance its proactive engagement capabilities (e.g., `proactive_engagement_skill.py`). Instead of just starting a generic conversation, it could provide timely, personalized updates like, "I saw a new article on that machine learning library you're interested in. The key takeaway is a 10% performance improvement in the latest version. Would you like the link or a more detailed summary?" This makes Praxis a more active and relevant information curator.

### Advanced Task & Development Assistance (Future Aspirations)

These skills aim to elevate Praxis into a more capable assistant for complex tasks and development workflows.

*   **Interactive Code Debugging Assistant:**
    *   **Concept:** Make the power of the CIQ "Test & Repair" loop directly available to the user. A user could paste a block of code (or point to a file) and say, "This isn't working, can you help me debug it?" Praxis would then attempt to understand the code's purpose (perhaps by asking clarifying questions or analyzing docstrings/comments), write or infer potential unit tests, execute them (in a sandboxed environment), analyze any errors, and use the LLM to suggest specific fixes or explanations.
    *   **Why it's valuable:** This would transform Praxis into a powerful pair-programming partner, capable of actively assisting with debugging, code understanding, and iterative refinement, leveraging its existing CIQ framework.

*   **End-to-End Project Management Skill:**
    *   **Concept:** A high-level skill that can manage a simple software project from initiation to basic setup. For example, a user could say, "Start a new Python project called 'my_utility_app'." Praxis could then:
        *   Create a project directory (using `file_manager_skill.py`).
        *   Initialize a Git repository locally.
        *   Optionally, create the repository on GitHub (using `github_api_interaction_skill.py` if available and configured) and link the local repo.
        *   Create template files (e.g., `README.md`, `.gitignore`, a basic `main.py`).
        *   Potentially track initial tasks in a local Markdown file or a simple issue in the KnowledgeBase.
    *   **Why it's valuable:** This would synthesize many of its existing capabilities into a cohesive, high-level workflow, demonstrating its ability to handle complex, multi-step tasks and automate common developer setup routines.
