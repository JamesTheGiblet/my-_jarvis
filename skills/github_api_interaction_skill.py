# C:\Users\gilbe\Desktop\self-evolving-ai\skills\github_api_interaction_skill.py

import os
import requests # For actual API calls
import json
import logging # Use standard logging
from typing import Dict, Any, List, Tuple, Optional

# --- Module-level configuration ---
BASE_API_URL = "https://api.github.com"
API_TOKEN = os.getenv("GITHUB_API_TOKEN")

if not API_TOKEN:
    logging.warning("[github_skill] GITHUB_API_TOKEN not found in environment variables. Some actions may be rate-limited or fail.")

def _call_github_api(endpoint: str, method: str = "GET", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Helper method to make calls to the GitHub API.
    Returns (success_bool, result_dict_or_error_dict).
    """
    url = f"{BASE_API_URL}{endpoint}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    try:
        response = requests.request(method, url, headers=headers, params=params, json=data, timeout=15)
        logging.debug(f"[_call_github_api] API Call: {method} {url} - Status: {response.status_code}")
        response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
        return True, response.json()
    except requests.exceptions.HTTPError as e:
        error_details = {"error_type": "http_error", "status_code": e.response.status_code, "message": str(e)}
        try: # Try to get more details from GitHub's error response
            error_details["github_message"] = e.response.json().get("message", "No specific GitHub error message.")
        except json.JSONDecodeError:
            error_details["github_message"] = "Failed to parse GitHub error response."
        logging.error(f"[_call_github_api] HTTPError calling GitHub API: {error_details}", exc_info=True)
        return False, error_details
    except requests.exceptions.RequestException as e:
        logging.error(f"[_call_github_api] RequestException calling GitHub API: {e}", exc_info=True)
        return False, {"error_type": "request_exception", "message": str(e)}
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"[_call_github_api] Unexpected error calling GitHub API: {e}", exc_info=True)
        return False, {"error_type": "unexpected_error", "message": str(e)}

def get_github_repo_info(context, repo_full_name: str):
    """
    Fetches information about a GitHub repository.
    Args:
        context: The skill context.
        repo_full_name (str): The full name of the repository (e.g., "owner/repo_name").
    """
    if not repo_full_name or '/' not in repo_full_name:
        context.speak("Sir, please provide the repository name in the format 'owner/repository'.")
        return

    context.speak(f"Fetching information for GitHub repository: {repo_full_name}...")
    success, data = _call_github_api(f"/repos/{repo_full_name}")

    if success:
        repo_name = data.get("name", "N/A")
        description = data.get("description", "No description provided.")
        stars = data.get("stargazers_count", 0)
        forks = data.get("forks_count", 0)
        language = data.get("language", "N/A")
        url = data.get("html_url", "#")
        context.speak(f"Repository: {repo_name}. Language: {language}. Stars: {stars}. Forks: {forks}.")
        context.speak(f"Description: {description}")
        context.speak(f"URL: {url}")
        logging.info(f"Successfully fetched repo info for {repo_full_name}")
    else:
        error_message = data.get("github_message") or data.get("message", "Unknown error")
        context.speak(f"I'm sorry, sir. I couldn't fetch repository information for {repo_full_name}. Error: {error_message}")
        logging.error(f"Failed to fetch repo info for {repo_full_name}: {data}")

def get_github_user_info(context, username: str):
    """
    Fetches information about a GitHub user.
    Args:
        context: The skill context.
        username (str): The GitHub username.
    """
    if not username:
        context.speak("Sir, please provide a GitHub username.")
        return

    context.speak(f"Fetching information for GitHub user: {username}...")
    success, data = _call_github_api(f"/users/{username}")

    if success:
        user_login = data.get("login", "N/A")
        name = data.get("name", user_login) # Fallback to login if name is not set
        bio = data.get("bio", "No bio provided.")
        followers = data.get("followers", 0)
        following = data.get("following", 0)
        public_repos = data.get("public_repos", 0)
        url = data.get("html_url", "#")
        context.speak(f"User: {name} ({user_login}). Public Repos: {public_repos}. Followers: {followers}. Following: {following}.")
        context.speak(f"Bio: {bio}")
        context.speak(f"Profile URL: {url}")
        logging.info(f"Successfully fetched user info for {username}")
    else:
        error_message = data.get("github_message") or data.get("message", "Unknown error")
        context.speak(f"I'm sorry, sir. I couldn't fetch user information for {username}. Error: {error_message}")
        logging.error(f"Failed to fetch user info for {username}: {data}")

# TODO: Implement other GitHub skill functions like list_issues, get_issue, create_issue etc.
# Each would follow a similar pattern: define function, call _call_github_api, process results, speak.

def _test_skill(context):
    """
    Runs a quick self-test for the github_api_interaction_skill module.
    It attempts to fetch info for a known GitHub user.
    """
    logging.info("[github_skill_test] Running self-test for github_api_interaction_skill module...")
    try:
        test_username = "octocat" # A well-known GitHub user for testing

        # Test 1: Call get_github_user_info
        # This will be muted by the SkillContext during testing.
        # The purpose is to see if it executes without raising an unhandled exception
        # and if the API call is attempted.
        logging.info(f"[github_skill_test] Attempting to call get_github_user_info for user: {test_username}")
        get_github_user_info(context, test_username)
        # If get_github_user_info itself logs errors (e.g., API issues), those will appear in the log.
        # The test passes if the skill completes without throwing an exception that _test_skill doesn't handle.

        logging.info(f"[github_skill_test] get_github_user_info skill call completed for {test_username} (check logs for API interaction details).")
        logging.info("[github_skill_test] All github_api_interaction_skill self-tests passed successfully.")
    except Exception as e:
        logging.error(f"[github_skill_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py