# skills/system_management_skills.py
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import SkillContext # Assuming SkillContext is in main.py or accessible

def trigger_skill_refinement_cycle(context: 'SkillContext', num_skills_to_attempt: int = 1) -> bool:
    """
    Initiates a skill refinement cycle to identify and attempt to fix underperforming skills.
    Args:
        context: The skill context.
        num_skills_to_attempt (int): The maximum number of skills the agent should attempt to refine in this cycle.
    """
    if not hasattr(context._praxis_core_ref, 'skill_refinement_agent_instance') or \
       not context._praxis_core_ref.skill_refinement_agent_instance:
        context.speak("The skill refinement agent is not available or not initialized.")
        logging.warning("SkillRefinement: trigger_skill_refinement_cycle called but agent not found in PraxisCore.")
        return False

    agent = context._praxis_core_ref.skill_refinement_agent_instance
    
    context.speak(f"Understood. Initiating a skill refinement cycle. I will attempt to refine up to {num_skills_to_attempt} skill(s). This may take a moment.")
    
    # Run the refinement cycle in a separate thread to avoid blocking the main loop
    refinement_thread = threading.Thread(target=agent.run_refinement_cycle, args=(num_skills_to_attempt,), daemon=True)
    refinement_thread.start()
    
    logging.info(f"SkillRefinement: Triggered refinement cycle for up to {num_skills_to_attempt} skill(s).")
    return True # Skill successfully triggered the agent