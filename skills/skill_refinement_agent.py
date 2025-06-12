# skills/skill_refinement_agent.py
import logging
import os
import inspect
import ast # For more robust parsing of Python files
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime

# Ensure the main project directory is in PYTHONPATH
# This assumes skill_refinement_agent.py is in the 'skills' subdirectory.
project_root_for_imports = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root_for_imports not in os.sys.path:
    os.sys.path.insert(0, project_root_for_imports)

try:
    import knowledge_base as kb
    from brain import generate_code_with_llm # For suggesting code fixes
    from config import model as llm_model # The LLM model instance
    # Import prompt_tuning_agent if its constants/functions are directly used by this agent
    # If it's only called via context.skills_registry, this import might not be needed here.
    # Based on previous context, it seems _get_brain_py_content_for_prompt_tuner needs it.
    from skills import prompt_tuning_agent
except ImportError as e:
    logging.critical(f"SkillRefinementAgent: Critical import error: {e}. Agent may not function.", exc_info=True)
    kb = None
    generate_code_with_llm = None
    llm_model = None
    prompt_tuning_agent = None


# Define SKILLS_DIR relative to this file's location (skills directory)
# then go up one level to the project root to define PROPOSED_FIXES_DIR relative to that.
_SKILLS_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT_DIR = os.path.abspath(os.path.join(_SKILLS_MODULE_DIR, ".."))

SKILLS_DIR_ABS_PATH = _SKILLS_MODULE_DIR # The directory containing skill modules
PROPOSED_FIXES_DIR_REL = "skills/proposed_fixes" # Relative to project root
PROPOSED_FIXES_DIR_ABS_PATH = os.path.join(_PROJECT_ROOT_DIR, PROPOSED_FIXES_DIR_REL)


def _ensure_proposed_fixes_dir_exists() -> str:
    """Ensures the directory for proposed fixes exists and returns its absolute path."""
    if not os.path.exists(PROPOSED_FIXES_DIR_ABS_PATH):
        try:
            os.makedirs(PROPOSED_FIXES_DIR_ABS_PATH)
            logging.info(f"SkillRefinementAgent: Created directory for proposed fixes at {PROPOSED_FIXES_DIR_ABS_PATH}")
        except Exception as e:
            logging.error(f"SkillRefinementAgent: Failed to create directory {PROPOSED_FIXES_DIR_ABS_PATH}: {e}", exc_info=True)
            raise
    return PROPOSED_FIXES_DIR_ABS_PATH


class SkillRefinementAgent:
    def __init__(self, skills_registry: Optional[Dict[str, callable]] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.skills_registry = skills_registry
        if not all([kb, generate_code_with_llm, llm_model, prompt_tuning_agent]):
            self.logger.error("SkillRefinementAgent initialized with missing critical components due to import errors.")
            # Consider raising an error or setting a flag to prevent operation

    def _get_skill_source_code(self, skill_name: str) -> Optional[str]:
        """
        Retrieves the source code of a given skill's defining file.
        Primary strategy: Uses the skills_registry and inspect module.
        Fallback strategy: Recursively searches SKILLS_DIR_ABS_PATH and uses AST parsing.
        """
        if self.skills_registry:
            skill_callable = self.skills_registry.get(skill_name)
            if skill_callable and callable(skill_callable):
                try:
                    skill_file_path = inspect.getfile(skill_callable)
                    if os.path.exists(skill_file_path):
                        with open(skill_file_path, "r", encoding="utf-8") as f:
                            self.logger.info(f"Found skill '{skill_name}' source via registry: {skill_file_path}")
                            return f.read()
                    else:
                        self.logger.warning(f"File path from inspect for skill '{skill_name}' does not exist: {skill_file_path}")
                except TypeError:
                    self.logger.warning(f"Could not get file for skill '{skill_name}' (possibly a built-in or C extension).")
                except Exception as e:
                    self.logger.error(f"Error getting skill source for '{skill_name}' via inspect: {e}")
            else:
                self.logger.info(f"Skill '{skill_name}' not found in provided skills_registry or not callable.")

        self.logger.info(f"Falling back to file search for skill '{skill_name}' in {SKILLS_DIR_ABS_PATH}")
        for root, _, files in os.walk(SKILLS_DIR_ABS_PATH):
            if os.path.commonpath([root, PROPOSED_FIXES_DIR_ABS_PATH]) == PROPOSED_FIXES_DIR_ABS_PATH:
                continue # Skip the proposed_fixes directory

            for filename in files:
                if filename.endswith(".py"):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        tree = ast.parse(content, filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef) and node.name == skill_name:
                                self.logger.info(f"Found skill '{skill_name}' definition in file '{file_path}' via AST.")
                                return content # Return the whole file content
                        if filename == f"{skill_name}.py": # Fallback to filename match
                             self.logger.info(f"Found skill '{skill_name}' by filename match: {file_path}")
                             return content
                    except SyntaxError:
                        self.logger.warning(f"SyntaxError parsing {file_path}, cannot use AST. Trying string search.")
                        if f"def {skill_name}(" in content or f"async def {skill_name}(" in content:
                             self.logger.info(f"Found skill '{skill_name}' in file '{file_path}' via string search.")
                             return content
                    except Exception as e:
                        self.logger.error(f"Error processing potential skill file {file_path}: {e}")
        self.logger.warning(f"Source code for skill '{skill_name}' not found after full search.")
        return None

    def identify_and_prioritize_skills(self, top_n: int = 3) -> List[Dict[str, Any]]:
        if not kb:
            self.logger.error("KnowledgeBase not available for identifying skills.")
            return []
        self.logger.info("Identifying skills for refinement...")
        candidate_skills = {}
        skills_with_neg_feedback = kb.get_skills_with_negative_feedback()
        for item in skills_with_neg_feedback:
            skill_name = item['skill_name']
            if skill_name not in candidate_skills:
                candidate_skills[skill_name] = {'user_feedback_count': 0, 'automated_failure_count': 0, 'comments': [], 'errors': []}
            candidate_skills[skill_name]['user_feedback_count'] += item['negative_feedback_count']
            candidate_skills[skill_name]['comments'].extend(item['recent_comments'])

        failing_skills_auto = kb.get_skill_failure_rates(top_n=top_n * 2, min_usage=3)
        for item in failing_skills_auto:
            skill_name = item['skill_name']
            if skill_name not in candidate_skills:
                candidate_skills[skill_name] = {'user_feedback_count': 0, 'automated_failure_count': 0, 'comments': [], 'errors': []}
            candidate_skills[skill_name]['automated_failure_count'] += item['failure_count']
            recent_errors = kb.get_recent_skill_failures(skill_name=skill_name, limit=3)
            candidate_skills[skill_name]['errors'].extend([f"Error on {e['timestamp']}: {e['error_message']} (Args: {e['args_used']})" for e in recent_errors])

        prioritized_list = []
        for skill_name, data in candidate_skills.items():
            score = (data['user_feedback_count'] * 10) + (data['automated_failure_count'] * 3)
            if score > 0:
                prioritized_list.append({"skill_name": skill_name, "score": score, "details": data})
        prioritized_list.sort(key=lambda x: x['score'], reverse=True)
        self.logger.info(f"Identified {len(prioritized_list)} candidate skills for refinement. Top {top_n}: {[s['skill_name'] for s in prioritized_list[:top_n]]}")
        return prioritized_list[:top_n]

    def _get_brain_py_content(self) -> Optional[str]:
        """Helper to read brain.py content for prompt tuning suggestions."""
        if not prompt_tuning_agent:
            self.logger.error("PromptTuningAgent module not available to get BRAIN_FILE_PATH.")
            return None
        # brain.py is in the project root, which is one level up from the 'skills' directory
        brain_path_full = os.path.join(_PROJECT_ROOT_DIR, prompt_tuning_agent.BRAIN_FILE_PATH)
        try:
            with open(brain_path_full, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Could not find {prompt_tuning_agent.BRAIN_FILE_PATH} at {brain_path_full} for prompt tuning.")
            return None
        except Exception as e:
            self.logger.error(f"Error reading {prompt_tuning_agent.BRAIN_FILE_PATH} for prompt tuning: {e}", exc_info=True)
            return None

    def attempt_skill_refinement(self, context: Any, skill_details: Dict[str, Any]) -> Optional[str]:
        """
        Attempts to refine a single skill identified from KB using the LLM.
        Saves the proposed fix to a file for review.
        """
        if not generate_code_with_llm or not llm_model:
            self.logger.error("LLM components not available for skill refinement.")
            context.speak("The LLM components needed for skill refinement are not available.")
            return None

        skill_name = skill_details['skill_name']
        self.logger.info(f"Attempting refinement for skill: {skill_name}")
        context.speak(f"Attempting to refine the skill '{skill_name}'.")

        source_code = self._get_skill_source_code(skill_name)
        if not source_code:
            self.logger.error(f"Could not retrieve source code for skill '{skill_name}'. Aborting refinement attempt.")
            context.speak(f"I could not find the source code for '{skill_name}' to refine it.")
            return None

        problem_description = f"The skill '{skill_name}' needs refinement. \n"
        problem_description += "Current source code:\n```python\n" + source_code + "\n```\n\n"
        
        type_error_count = 0
        arg_related_keywords = ["argument", "parameter", "missing", "required", "typeerror"]
        num_errors_for_heuristic = 0

        if skill_details['details']['errors']:
            problem_description += "It has experienced the following automated errors:\n"
            for error_detail_str in skill_details['details']['errors']:
                problem_description += f"- {error_detail_str}\n"
                error_msg_lower = error_detail_str.lower()
                if "typeerror" in error_msg_lower or any(keyword in error_msg_lower for keyword in arg_related_keywords):
                    type_error_count += 1
                num_errors_for_heuristic +=1
            problem_description += "\n"

        if skill_details['details']['comments']:
            problem_description += "It has also received the following user feedback:\n"
            for comment in skill_details['details']['comments']:
                problem_description += f"- {comment}\n"
            problem_description += "\n"
        
        # Heuristic: If many recent errors are argument-related, suggest prompt tuning first.
        if num_errors_for_heuristic > 0 and (type_error_count / num_errors_for_heuristic) >= 0.5:
            context.speak(f"Many recent errors for '{skill_name}' appear to be argument-related. I will first suggest a prompt tuning review.")
            self.logger.info(f"Highlighting argument-related errors for '{skill_name}'. Triggering prompt tuning suggestion.")
            if prompt_tuning_agent and hasattr(prompt_tuning_agent, "_generate_and_save_prompt_suggestion"):
                brain_content = self._get_brain_py_content()
                if brain_content:
                    prompt_tuning_agent._generate_and_save_prompt_suggestion(
                        context, 
                        f"The skill '{skill_name}' frequently encounters argument-related errors (e.g., TypeErrors). Review its invocation in the main prompt.",
                        brain_content
                    )
                else:
                    context.speak("Could not retrieve brain.py content for prompt tuning.")
                return None # Exit skill refinement for now
            else:
                context.speak("Prompt tuning agent is not available to suggest changes.")


        problem_description += "Please analyze the issues and provide an improved and complete version of the skill's Python code. Ensure your response is ONLY the Python code block."
        
        proposed_code, p_tokens, r_tokens = generate_code_with_llm(problem_description, llm_model, ai_name="SkillRefinementExpert")
        self.logger.info(f"LLM call for '{skill_name}' refinement: Prompt Tokens: {p_tokens}, Response Tokens: {r_tokens}")

        if proposed_code:
            # Try to get original module name from skill_file_path if available
            original_module_name = skill_name # Fallback
            skill_callable = self.skills_registry.get(skill_name) if self.skills_registry else None
            if skill_callable:
                try:
                    skill_file_path = inspect.getfile(skill_callable)
                    original_module_name = os.path.basename(skill_file_path).replace('.py', '')
                except TypeError:
                    pass # Keep skill_name as fallback

            proposal_filename = f"fixed_{original_module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            proposal_filepath = os.path.join(_ensure_proposed_fixes_dir_exists(), proposal_filename)
            try:
                with open(proposal_filepath, "w", encoding="utf-8") as f:
                    f.write(f"# Fix proposed by SkillRefinementAgent for: {skill_name} (Original module: {original_module_name}.py)\n")
                    f.write(f"# Based on score: {skill_details.get('score', 'N/A')}\n\n")
                    f.write(proposed_code)
                self.logger.info(f"Proposed fix for '{skill_name}' saved to: {proposal_filepath}")
                context.speak(f"A proposed fix for skill '{skill_name}' has been generated and saved to '{PROPOSED_FIXES_DIR_REL}/{proposal_filename}' for your review, sir.")
                return proposal_filepath
            except Exception as e:
                self.logger.error(f"Error saving proposed fix for '{skill_name}': {e}", exc_info=True)
                context.speak(f"I generated a fix for '{skill_name}', but encountered an error saving it.")
        else:
            self.logger.warning(f"LLM did not provide a proposed fix for skill '{skill_name}'.")
            context.speak(f"The LLM was unable to provide a fix for '{skill_name}' at this time.")
        return None

    def attempt_refinement_of_proposed_skill(self, context: Any, proposed_skill_file_path: str, test_failure_details: str) -> None:
        """
        Attempts to refine a newly proposed skill that failed its initial _test_skill.
        Args:
            context: The skill context from the calling agent (e.g., SkillReviewAgent).
            proposed_skill_file_path (str): Absolute path to the failing proposed skill .py file.
            test_failure_details (str): String containing details of why the _test_skill failed.
        """
        if not generate_code_with_llm or not llm_model:
            context.speak("The LLM components needed for skill refinement are not available.")
            self.logger.error("SkillRefinementAgent: LLM components not available for refining proposed skill.")
            return

        skill_filename = os.path.basename(proposed_skill_file_path)
        self.logger.info(f"Attempting refinement for PROPOSED skill: {skill_filename} located at {proposed_skill_file_path}")
        context.speak(f"Attempting to generate a fix for the proposed skill '{skill_filename}'.")

        try:
            with open(proposed_skill_file_path, 'r', encoding='utf-8') as f:
                skill_source_code = f.read()
            self.logger.info(f"Successfully read source code for proposed skill '{skill_filename}'.")
        except Exception as e:
            context.speak(f"Failed to read the source code for proposed skill '{skill_filename}'. Error: {e}")
            self.logger.error(f"Error reading source for proposed skill {skill_filename}: {e}", exc_info=True)
            return

        problem_description = f"The PROPOSED skill '{skill_filename}' failed its initial _test_skill function.\n"
        problem_description += "Original source code of the proposed skill:\n```python\n" + skill_source_code + "\n```\n\n"
        problem_description += "The _test_skill failed with the following details:\n" + test_failure_details + "\n\n"
        problem_description += "Please analyze the original code and the failure details, then provide an improved and complete version of the skill's Python code. Ensure your response is ONLY the Python code block."

        proposed_fix_code, p_tokens, r_tokens = generate_code_with_llm(problem_description, llm_model, ai_name="SkillCorrectionExpert")
        self.logger.info(f"LLM call for PROPOSED skill '{skill_filename}' refinement: Prompt Tokens: {p_tokens}, Response Tokens: {r_tokens}")

        if proposed_fix_code:
            base_original_filename = skill_filename.replace('.py', '')
            proposal_filename = f"fixed_PROPOSED_{base_original_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            proposal_filepath = os.path.join(_ensure_proposed_fixes_dir_exists(), proposal_filename)
            try:
                with open(proposal_filepath, "w", encoding="utf-8") as f:
                    f.write(f"# Fix proposed by SkillRefinementAgent for: {skill_filename}\n")
                    f.write(f"# Original test failure: {test_failure_details.splitlines()[0]}\n\n")
                    f.write(proposed_fix_code)
                self.logger.info(f"Proposed fix for PROPOSED skill '{skill_filename}' saved to: {proposal_filepath}")
                context.speak(f"A proposed fix for the new skill '{skill_filename}' has been generated. It is saved in the '{PROPOSED_FIXES_DIR_REL}' directory as '{proposal_filename}' for your review, sir.")
            except Exception as e:
                self.logger.error(f"Error saving proposed fix for PROPOSED skill '{skill_filename}': {e}", exc_info=True)
                context.speak(f"I generated a fix for '{skill_filename}', but encountered an error saving it.")
        else:
            self.logger.warning(f"LLM did not provide a proposed fix for PROPOSED skill '{skill_filename}'.")
            context.speak(f"The LLM was unable to provide a fix for the proposed skill '{skill_filename}' at this time.")

    def run_refinement_cycle(self, context: Any, num_skills_to_attempt: int = 1):
        """
        Runs a full cycle of identifying, prioritizing, and attempting refinement.
        """
        self.logger.info("Starting new skill refinement cycle...")
        prioritized_skills = self.identify_and_prioritize_skills(top_n=num_skills_to_attempt)

        if not prioritized_skills:
            self.logger.info("No skills identified for refinement in this cycle.")
            context.speak("No skills currently meet the criteria for automated refinement.")
            return

        refined_count = 0
        for i, skill_to_refine_details in enumerate(prioritized_skills):
            if i >= num_skills_to_attempt:
                break
            self.logger.info(f"Processing skill {i+1}/{num_skills_to_attempt}: {skill_to_refine_details['skill_name']} (Score: {skill_to_refine_details['score']})")
            if self.attempt_skill_refinement(context, skill_to_refine_details): # Pass context
                refined_count +=1
        
        if refined_count > 0:
            context.speak(f"Skill refinement cycle complete. I attempted to refine {refined_count} skill(s). Please check the '{PROPOSED_FIXES_DIR_REL}' directory for proposals.")
        else:
            context.speak("Skill refinement cycle complete. No fixes were successfully generated in this cycle.")
        self.logger.info("Skill refinement cycle finished.")

def _test_skill(context: Any) -> None:
    """Placeholder test for the skill refinement agent. Full testing is complex."""
    logging.info("SkillRefinementAgent: _test_skill called. (Note: Full test requires mock KB and LLM).")
    # In a real test, you'd mock context.kb, context.skills_registry, and context.chat_session.send_message
    # For now, just ensure it can be called.
    # Example of how it might be called if it were a skill itself (though it's more of a system agent)
    # if hasattr(context._praxis_core_ref, 'skill_refinement_agent_instance'):
    #    agent = context._praxis_core_ref.skill_refinement_agent_instance
    #    agent.run_refinement_cycle(context, num_skills_to_attempt=1) # Pass context
    context.speak("Skill refinement agent self-test placeholder executed.")
    assert True # Basic assertion

if __name__ == "__main__":
    # This is for testing the agent directly.
    # In a real scenario, this might be triggered by a scheduler or another part of Praxis.
    if not all([kb, generate_code_with_llm, llm_model, prompt_tuning_agent]):
        print("Cannot run SkillRefinementAgent test: Missing critical components (kb, LLM function, model, or prompt_tuning_agent). Check logs.")
    else:
        print("Initializing Knowledge Base for test...")
        kb.init_db() # Ensure DB is ready
        
        # Example: Manually log some dummy feedback/failures if your DB is empty
        # This requires a dummy context for kb.record_skill_invocation if it uses context.speak
        class DummyContext:
            def __init__(self):
                self.skills_registry = {} # Empty for this test
                self.kb = kb # Direct access for logging
            def speak(self, message): print(f"DummyContext Speak: {message}")

        dummy_ctx = DummyContext()
        # kb.record_skill_invocation("example_failing_skill", False, error_message="Test error 1")
        # kb.record_interaction_feedback(interaction_id_of_example_skill, "negative", "It didn't work as expected")

        # When running standalone, we don't have the main SKILLS registry from PraxisCore.
        # The agent will rely on its fallback file search mechanism for _get_skill_source_code.
        agent = SkillRefinementAgent(skills_registry=None) 

        print("Running refinement cycle (will attempt to refine up to 1 skill)...")
        # The run_refinement_cycle method now needs a context.
        # For standalone testing, we provide a simplified context.
        agent.run_refinement_cycle(dummy_ctx, num_skills_to_attempt=1)
        print("Refinement cycle test complete. Check logs and 'skills/proposed_fixes/' directory.")

