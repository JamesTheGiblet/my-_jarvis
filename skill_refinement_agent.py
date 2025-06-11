# skill_refinement_agent.py
from datetime import datetime
import os
import logging
import json
import inspect
import ast # For more robust parsing of Python files
from typing import List, Dict, Any, Optional, Tuple

# Ensure the main project directory is in PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in os.sys.path:
    os.sys.path.insert(0, project_root)

try:
    import knowledge_base as kb
    from brain import generate_code_with_llm # For suggesting code fixes
    from config import model as llm_model # The LLM model instance
except ImportError as e:
    logging.error(f"SkillRefinementAgent: Critical import error: {e}. Agent may not function.", exc_info=True)
    kb = None
    generate_code_with_llm = None
    llm_model = None

SKILLS_DIR = os.path.join(project_root, "skills")
PROPOSED_FIXES_DIR = os.path.join(SKILLS_DIR, "proposed_fixes")

if not os.path.exists(PROPOSED_FIXES_DIR):
    os.makedirs(PROPOSED_FIXES_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SkillRefinementAgent:
    def __init__(self, skills_registry: Optional[Dict[str, callable]] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.skills_registry = skills_registry
        if not all([kb, generate_code_with_llm, llm_model]):
            self.logger.error("SkillRefinementAgent initialized with missing critical components due to import errors.")
            # You might want to raise an exception here or handle this state appropriately

    def _get_skill_source_code(self, skill_name: str) -> Optional[str]:
        """
        Retrieves the source code of a given skill's defining file.
        Primary strategy: Uses the skills_registry and inspect module.
        Fallback strategy: Recursively searches SKILLS_DIR and uses AST parsing.
        """
        # Primary Strategy: Use skills_registry if available
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

        self.logger.info(f"Falling back to file search for skill '{skill_name}' in {SKILLS_DIR}")
        # Fallback Strategy: Recursive search and AST parsing
        for root, _, files in os.walk(SKILLS_DIR):
            # Skip the proposed_fixes directory to avoid circular dependencies or analyzing proposals
            if os.path.commonpath([root, PROPOSED_FIXES_DIR]) == PROPOSED_FIXES_DIR:
                continue

            for filename in files:
                if filename.endswith(".py"):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Try parsing with AST to find the function definition
                        try:
                            tree = ast.parse(content, filename=file_path)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef) and node.name == skill_name:
                                    self.logger.info(f"Found skill '{skill_name}' definition in file '{file_path}' via AST.")
                                    return content # Return the whole file content
                        except SyntaxError:
                            self.logger.warning(f"SyntaxError parsing {file_path}, cannot use AST. Will try string search.")
                            # Fallback to simpler string search if AST fails (e.g., for Python 2 code or invalid syntax)
                            if f"def {skill_name}(" in content or f"async def {skill_name}(" in content:
                                self.logger.info(f"Found skill '{skill_name}' in file '{file_path}' via string search.")
                                return content

                        # If skill_name matches filename (e.g., skill_name.py)
                        if filename == f"{skill_name}.py":
                             self.logger.info(f"Found skill '{skill_name}' by filename match: {file_path}")
                             return content

                    except Exception as e:
                        self.logger.error(f"Error processing potential skill file {file_path}: {e}")
            
        self.logger.warning(f"Source code for skill '{skill_name}' not found after full search.")
        return None

    def identify_and_prioritize_skills(self, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Identifies skills needing refinement based on negative feedback and failure rates,
        then prioritizes them.
        """
        if not kb:
            self.logger.error("KnowledgeBase not available for identifying skills.")
            return []
            
        self.logger.info("Identifying skills for refinement...")
        candidate_skills = {}

        # 1. Get skills with negative user feedback
        skills_with_neg_feedback = kb.get_skills_with_negative_feedback()
        for item in skills_with_neg_feedback:
            skill_name = item['skill_name']
            if skill_name not in candidate_skills:
                candidate_skills[skill_name] = {'user_feedback_count': 0, 'automated_failure_count': 0, 'comments': [], 'errors': []}
            candidate_skills[skill_name]['user_feedback_count'] += item['negative_feedback_count']
            candidate_skills[skill_name]['comments'].extend(item['recent_comments'])

        # 2. Get skills with high automated failure rates
        # We might want to fetch more than top_n here to combine scores effectively
        failing_skills_auto = kb.get_skill_failure_rates(top_n=top_n * 2, min_usage=3) # Get more to allow for diverse scoring
        for item in failing_skills_auto:
            skill_name = item['skill_name']
            if skill_name not in candidate_skills:
                candidate_skills[skill_name] = {'user_feedback_count': 0, 'automated_failure_count': 0, 'comments': [], 'errors': []}
            # Use actual failure count, not rate, for scoring consistency
            candidate_skills[skill_name]['automated_failure_count'] += item['failure_count']
            
            # Get specific error messages for these automated failures
            recent_errors = kb.get_recent_skill_failures(skill_name=skill_name, limit=3)
            candidate_skills[skill_name]['errors'].extend([f"Error on {e['timestamp']}: {e['error_message']} (Args: {e['args_used']})" for e in recent_errors])

        # 3. Prioritization (simple scoring for now)
        prioritized_list = []
        for skill_name, data in candidate_skills.items():
            # Weighted score: user feedback is more critical
            score = (data['user_feedback_count'] * 10) + (data['automated_failure_count'] * 3)
            if score > 0: # Only consider skills with some indication of issues
                prioritized_list.append({
                    "skill_name": skill_name,
                    "score": score,
                    "details": data
                })
        
        prioritized_list.sort(key=lambda x: x['score'], reverse=True)
        self.logger.info(f"Identified {len(prioritized_list)} candidate skills for refinement. Top {top_n}: {[s['skill_name'] for s in prioritized_list[:top_n]]}")
        return prioritized_list[:top_n]

    def attempt_skill_refinement(self, skill_details: Dict[str, Any]) -> Optional[str]:
        """
        Attempts to refine a single skill using the LLM.
        Saves the proposed fix to a file for review.
        """
        if not generate_code_with_llm or not llm_model:
            self.logger.error("LLM components not available for skill refinement.")
            return None

        skill_name = skill_details['skill_name']
        self.logger.info(f"Attempting refinement for skill: {skill_name}")

        source_code = self._get_skill_source_code(skill_name)
        if not source_code:
            self.logger.error(f"Could not retrieve source code for skill '{skill_name}'. Aborting refinement attempt.")
            return None

        # Construct a detailed problem description for the LLM
        problem_description = f"The skill '{skill_name}' needs refinement. \n"
        problem_description += "Current source code:\n```python\n" + source_code + "\n```\n\n"
        
        if skill_details['details']['comments']:
            problem_description += "It has received the following user feedback:\n"
            for comment in skill_details['details']['comments']:
                problem_description += f"- {comment}\n"
            problem_description += "\n"

        if skill_details['details']['errors']:
            problem_description += "It has also experienced the following automated errors:\n"
            for error in skill_details['details']['errors']:
                problem_description += f"- {error}\n"
            problem_description += "\n"
        
        problem_description += "Please analyze the issues and provide an improved and complete version of the skill's Python code. Ensure your response is ONLY the Python code block."

        # Use generate_code_with_llm or a similar function tailored for refinement
        # The existing generate_code_with_llm might work if the prompt is clear enough.
        # We are not using its 'test & repair' feature here, but its direct generation.
        proposed_code, p_tokens, r_tokens = generate_code_with_llm(problem_description, llm_model, ai_name="SkillRefinementExpert")
        self.logger.info(f"LLM call for '{skill_name}' refinement: Prompt Tokens: {p_tokens}, Response Tokens: {r_tokens}")

        if proposed_code:
            proposal_filename = f"{skill_name}_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            proposal_filepath = os.path.join(PROPOSED_FIXES_DIR, proposal_filename)
            try:
                with open(proposal_filepath, "w", encoding="utf-8") as f:
                    f.write(proposed_code)
                self.logger.info(f"Proposed fix for '{skill_name}' saved to: {proposal_filepath}")
                return proposal_filepath
            except Exception as e:
                self.logger.error(f"Error saving proposed fix for '{skill_name}': {e}")
        else:
            self.logger.warning(f"LLM did not provide a proposed fix for skill '{skill_name}'.")
        return None

    def run_refinement_cycle(self, num_skills_to_attempt: int = 1):
        """
        Runs a full cycle of identifying, prioritizing, and attempting refinement.
        """
        self.logger.info("Starting new skill refinement cycle...")
        prioritized_skills = self.identify_and_prioritize_skills(top_n=num_skills_to_attempt)

        if not prioritized_skills:
            self.logger.info("No skills identified for refinement in this cycle.")
            return

        for i, skill_to_refine in enumerate(prioritized_skills):
            if i >= num_skills_to_attempt:
                break
            self.logger.info(f"Processing skill {i+1}/{num_skills_to_attempt}: {skill_to_refine['skill_name']} (Score: {skill_to_refine['score']})")
            self.attempt_skill_refinement(skill_to_refine)
        
        self.logger.info("Skill refinement cycle finished.")

if __name__ == "__main__":
    # This is for testing the agent directly.
    # In a real scenario, this might be triggered by a scheduler or another part of Praxis.
    if not all([kb, generate_code_with_llm, llm_model]):
        print("Cannot run SkillRefinementAgent test: Missing critical components (kb, LLM function, or model). Check logs.")
    else:
        print("Initializing Knowledge Base for test...")
        kb.init_db() # Ensure DB is ready
        
        # Example: Manually log some dummy feedback/failures if your DB is empty
        # kb.record_skill_invocation("example_failing_skill", False, error_message="Test error 1")
        # kb.record_interaction_feedback(interaction_id_of_example_skill, "negative", "It didn't work as expected")

        # When running standalone, we don't have the main SKILLS registry.
        # The agent will rely on its fallback file search mechanism.
        agent = SkillRefinementAgent(skills_registry=None) 

        print("Running refinement cycle (will attempt to refine up to 1 skill)...")
        agent.run_refinement_cycle(num_skills_to_attempt=1)
        print("Refinement cycle test complete. Check logs and 'skills/proposed_fixes/' directory.")