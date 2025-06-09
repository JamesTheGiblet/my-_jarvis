# skills/file_manager.py
import os
import logging
from typing import Any, Optional, List

# --- Configuration ---
SANDBOX_DIR_NAME = "praxis_sandbox"  # Name of the sandbox directory

# --- Helper Functions ---

def _get_sandbox_abs_path() -> str:
    """Returns the absolute path to the sandbox directory."""
    # Assuming main.py is in the project root, this creates the sandbox
    # in the project root.
    return os.path.abspath(SANDBOX_DIR_NAME)

def _ensure_sandbox_dir_exists() -> None:
    """Ensures the sandbox directory exists, creating it if necessary."""
    sandbox_path = _get_sandbox_abs_path()
    if not os.path.exists(sandbox_path):
        try:
            os.makedirs(sandbox_path)
            logging.info(f"FileManager: Created sandbox directory at {sandbox_path}")
        except Exception as e:
            logging.error(f"FileManager: Failed to create sandbox directory at {sandbox_path}: {e}", exc_info=True)
            # This is a critical failure for the skill's safety
            raise RuntimeError(f"Could not create sandbox directory: {sandbox_path}") from e

def _get_sandboxed_path(context: Any, user_path: str, check_exists: bool = False, is_for_writing: bool = False) -> Optional[str]:
    """
    Validates and converts a user-provided path to an absolute path within the sandbox.
    Prevents directory traversal.
    Args:
        context: The skill context for speaking.
        user_path: The path provided by the user/LLM, relative to the sandbox.
        check_exists: If True, checks if the path exists.
        is_for_writing: If True, the path is intended for a write operation.
                        The existence check is slightly different (parent must exist).
    Returns:
        The absolute, validated path within the sandbox, or None if invalid/unsafe.
    """
    _ensure_sandbox_dir_exists() # Ensure sandbox base exists first
    abs_sandbox_dir = _get_sandbox_abs_path()

    # Normalize user_path: remove leading slashes and disallow absolute paths from user
    if os.path.isabs(user_path):
        context.speak("Error: Absolute paths are not allowed. Please provide a path relative to the sandbox.")
        logging.warning("FileManager: Attempt to use absolute path denied.")
        return None

    # Clean the path to prevent issues with joining, e.g. " /file.txt"
    cleaned_user_path = user_path.strip().lstrip('/\\')
    if not cleaned_user_path: # Handle empty or root-like paths after stripping
        context.speak("Error: A valid relative path within the sandbox is required.")
        return None

    prospective_path = os.path.join(abs_sandbox_dir, cleaned_user_path)
    normalized_path = os.path.abspath(prospective_path)

    # Security Check: Ensure the normalized path is within the sandbox
    if os.path.commonpath([abs_sandbox_dir, normalized_path]) != abs_sandbox_dir:
        context.speak("Error: Access denied. Path is outside the designated sandbox area.")
        logging.warning(f"FileManager: Sandbox escape attempt. User path: '{user_path}', Resolved: '{normalized_path}'")
        return None

    if check_exists and not is_for_writing and not os.path.exists(normalized_path):
        context.speak(f"Error: Path '{cleaned_user_path}' does not exist within the sandbox.")
        return None
    
    if is_for_writing:
        parent_dir = os.path.dirname(normalized_path)
        if not os.path.exists(parent_dir) or not os.path.isdir(parent_dir):
            context.speak(f"Error: Cannot write to '{cleaned_user_path}'. Parent directory does not exist within the sandbox.")
            return None
        if os.path.exists(normalized_path) and os.path.isdir(normalized_path):
            context.speak(f"Error: Cannot write file. Path '{cleaned_user_path}' is an existing directory.")
            return None

    return normalized_path

# --- Skill Functions ---

def list_directory_contents(context: Any, path: str = ".") -> None:
    """Lists files and subdirectories in a specified path within the sandbox. Defaults to sandbox root."""
    sandboxed_path = _get_sandboxed_path(context, path, check_exists=True)
    if not sandboxed_path or not os.path.isdir(sandboxed_path):
        if sandboxed_path: # Path was valid but not a directory
             context.speak(f"Error: '{path}' is not a directory within the sandbox.")
        return

    try:
        contents = os.listdir(sandboxed_path)
        if not contents:
            context.speak(f"The directory '{path}' is empty.")
        else:
            context.speak(f"Contents of '{path}':\n" + "\n".join(contents))
    except Exception as e:
        logging.error(f"FileManager: Error listing directory '{sandboxed_path}': {e}", exc_info=True)
        context.speak(f"Sorry, I couldn't list the contents of '{path}'.")

def read_file_content(context: Any, path: str) -> None:
    """Reads the content of a specified file within the sandbox."""
    sandboxed_path = _get_sandboxed_path(context, path, check_exists=True)
    if not sandboxed_path or not os.path.isfile(sandboxed_path):
        if sandboxed_path: # Path was valid but not a file
            context.speak(f"Error: '{path}' is not a file or does not exist within the sandbox.")
        return

    try:
        with open(sandboxed_path, 'r', encoding='utf-8') as f:
            content = f.read()
        context.speak(f"Content of '{path}':\n{content}")
    except Exception as e:
        logging.error(f"FileManager: Error reading file '{sandboxed_path}': {e}", exc_info=True)
        context.speak(f"Sorry, I couldn't read the file '{path}'.")

def write_content_to_file(context: Any, path: str, content: str) -> None:
    """Writes content to a specified file within the sandbox. Overwrites if exists, creates if not."""
    sandboxed_path = _get_sandboxed_path(context, path, is_for_writing=True)
    if not sandboxed_path:
        return

    try:
        with open(sandboxed_path, 'w', encoding='utf-8') as f:
            f.write(content)
        context.speak(f"Successfully wrote content to '{path}' in the sandbox.")
    except Exception as e:
        logging.error(f"FileManager: Error writing to file '{sandboxed_path}': {e}", exc_info=True)
        context.speak(f"Sorry, I couldn't write to the file '{path}'.")

def _test_skill(context: Any) -> None:
    """Tests the file manager skill operations. Called by main.py during skill loading."""
    logging.info("FileManager Skill Test: Starting...")
    # Ensure context.speak is muted and we can capture messages for assertions
    assert context.is_muted, "Context should be muted for _test_skill"
    context.clear_spoken_messages_for_test()

    _ensure_sandbox_dir_exists() # Make sure sandbox is there for tests
    sandbox_root = _get_sandbox_abs_path()

    test_dir = "test_subdir"
    test_file_relative = os.path.join(test_dir, "test_file.txt")
    test_content = "Hello from Praxis sandbox!"
    abs_test_dir = os.path.join(sandbox_root, test_dir)
    abs_test_file = os.path.join(sandbox_root, test_file_relative)

    # Cleanup before test, in case of previous failed run
    if os.path.exists(abs_test_file): os.remove(abs_test_file)
    if os.path.exists(abs_test_dir): os.rmdir(abs_test_dir)

    # Test 1: Create directory (implicitly by writing to a file in it)
    # For _get_sandboxed_path to allow writing, parent dir must exist.
    # So, we first ensure the sandbox root exists (done by _ensure_sandbox_dir_exists),
    # then _get_sandboxed_path will check if the parent of the target file (test_subdir_for_skill_test) exists.
    # Let's explicitly create the subdir for clarity in the test.
    os.makedirs(abs_test_dir, exist_ok=True)
    assert os.path.isdir(abs_test_dir), f"Test setup: Failed to create test directory {abs_test_dir}"

    # Test 2: Write content to a file
    write_content_to_file(context, test_file_relative, test_content)
    assert os.path.exists(abs_test_file), f"File {abs_test_file} was not created by write_content_to_file."
    with open(abs_test_file, 'r') as f:
        assert f.read() == test_content, "File content does not match what was written."
    assert f"Successfully wrote content to '{test_file_relative}' in the sandbox." in context.get_last_spoken_message_for_test()
    context.clear_spoken_messages_for_test()

    # Test reading
    read_file_content(context, test_file_relative)
    assert f"Content of '{test_file_relative}':\n{test_content}" in context.get_last_spoken_message_for_test()
    context.clear_spoken_messages_for_test()

    # Test listing
    list_directory_contents(context, test_dir)
    assert f"Contents of '{test_dir}':\n{os.path.basename(test_file_relative)}" in context.get_last_spoken_message_for_test()
    list_directory_contents(context, ".") # List sandbox root
    context.clear_spoken_messages_for_test()

    # Test path traversal attempt (should be denied by _get_sandboxed_path)
    logging.info("FileManager Skill Test: Testing path traversal denial...")
    read_file_content(context, "../outside_file.txt") # This should be blocked and speak an error
    assert "Error: Access denied. Path is outside the designated sandbox area." in context.get_last_spoken_message_for_test()
    context.clear_spoken_messages_for_test()

    # Cleanup (optional, but good for repeatable tests)
    if os.path.exists(abs_test_file):
        os.remove(abs_test_file)
    if os.path.exists(abs_test_dir):
        os.rmdir(abs_test_dir)

    logging.info("FileManager Skill Test: Completed.")

# Ensure sandbox exists when module is loaded, as a fallback.
# _ensure_sandbox_dir_exists() # Not strictly needed here if all skills call it.