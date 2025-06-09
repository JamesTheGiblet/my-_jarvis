# skills/analytics_skill.py
import logging
from typing import Optional

# SkillContext will provide access to knowledge_base functions via context.kb

def analyze_performance(context, query_type: str, skill_name: Optional[str] = None, period: str = "overall", count: int = 3):
    """
    Analyzes and reports on system performance based on stored metrics.
    Args:
        context: The skill context.
        query_type (str): Type of analysis to perform.
                          Expected values: "most_used_skills", "highest_failure_rates", 
                                           "recent_failures_for_skill", "all_recent_failures".
        skill_name (Optional[str]): Name of the skill for specific queries (e.g., recent_failures_for_skill).
        period (str): Time period for analysis (e.g., "today", "last_7_days", "overall"). Default is "overall".
        count (int): Number of records to retrieve for top N queries. Default is 3.
    """
    logging.info(f"Analyzing performance. Query Type: {query_type}, Skill: {skill_name}, Period: {period}, Count: {count}")

    if query_type == "most_used_skills":
        summary = context.kb.get_skill_usage_summary(period=period, top_n=count)
        if not summary:
            context.speak(f"I don't have any skill usage data for the period '{period}', sir.")
            return
        response = f"Here are the top {len(summary)} most used skills for the period '{period}':\n"
        for i, item in enumerate(summary):
            response += f"{i+1}. {item['skill_name']}: Used {item['usage_count']} times, Success Rate: {item['success_rate']:.2f}%.\n"
        context.speak(response.strip())

    elif query_type == "highest_failure_rates":
        rates = context.kb.get_skill_failure_rates(top_n=count)
        if not rates:
            context.speak("I couldn't find any skills with recorded failures meeting the criteria, sir.")
            return
        response = f"Here are the top {len(rates)} skills with the highest failure rates (minimum 1 usage):\n"
        for i, item in enumerate(rates):
            response += f"{i+1}. {item['skill_name']}: Failure Rate {item['failure_rate']:.2f}% ({item['failure_count']} failures / {item['usage_count']} uses).\n"
        context.speak(response.strip())

    elif query_type == "recent_failures_for_skill":
        if not skill_name:
            context.speak("Please specify a skill name to get recent failures for, sir.")
            return
        failures = context.kb.get_recent_skill_failures(skill_name=skill_name, limit=count)
        if not failures:
            context.speak(f"I have no recent failure records for the skill '{skill_name}', sir.")
            return
        response = f"Here are the last {len(failures)} recorded failures for '{skill_name}':\n"
        for i, fail in enumerate(failures):
            response += f"{i+1}. Timestamp: {fail['timestamp']}, Error: {fail['error_message'] or 'N/A'}, Args: {fail['args_used'] or 'N/A'}\n"
        context.speak(response.strip())

    elif query_type == "all_recent_failures":
        failures = context.kb.get_recent_skill_failures(limit=count)
        if not failures:
            context.speak("I have no recent failure records across all skills, sir.")
            return
        response = f"Here are the last {len(failures)} recorded failures across all skills:\n"
        for i, fail in enumerate(failures):
            response += f"{i+1}. Skill: {fail['skill_name']}, Timestamp: {fail['timestamp']}, Error: {fail['error_message'] or 'N/A'}, Args: {fail['args_used'] or 'N/A'}\n"
        context.speak(response.strip())

    else:
        context.speak(f"I'm sorry, sir, I don't recognize the analysis query type: '{query_type}'.")

def _test_skill(context):
    """Runs a quick self-test for the analytics_skill module."""
    logging.info("[analytics_skill_test] Running self-test for analytics_skill module...")
    try:
        # Simulate some data first if DB is empty for a more meaningful test
        # For a real test, you might want to ensure some data exists or mock context.kb
        # For now, we'll just call the functions and check they don't crash.
        # It's assumed the DB might be empty during a fresh test run.

        logging.info("[analytics_skill_test] Testing 'most_used_skills'...")
        analyze_performance(context, query_type="most_used_skills", period="overall", count=2)
        
        logging.info("[analytics_skill_test] Testing 'highest_failure_rates'...")
        analyze_performance(context, query_type="highest_failure_rates", count=2)

        # To make this test more robust, we'd ideally ensure a known skill exists.
        # For now, we'll use a common skill name that might exist or gracefully handle its absence.
        test_skill_for_failures = "web_search" 
        # First, record a dummy failure for this skill to ensure the query has something to find
        # This is a bit of a hack for a self-test; ideally, tests are isolated.
        try:
            context.kb.record_skill_invocation(test_skill_for_failures, success=False, error_message="Simulated test failure")
        except Exception as e:
            logging.warning(f"[analytics_skill_test] Could not record dummy failure for {test_skill_for_failures}: {e}")

        logging.info(f"[analytics_skill_test] Testing 'recent_failures_for_skill' for '{test_skill_for_failures}'...")
        analyze_performance(context, query_type="recent_failures_for_skill", skill_name=test_skill_for_failures, count=2)

        logging.info("[analytics_skill_test] Testing 'all_recent_failures'...")
        analyze_performance(context, query_type="all_recent_failures", count=2)

        logging.info("[analytics_skill_test] Testing invalid query_type...")
        analyze_performance(context, query_type="unknown_query_type")

        logging.info("[analytics_skill_test] analytics_skill self-test calls completed.")
    except Exception as e:
        logging.error(f"[analytics_skill_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise to signal failure to the loader