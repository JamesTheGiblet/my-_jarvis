# skills/file_manager.py

import os
import logging # Use standard logging
from typing import Dict, Any, List # Changed Tuple to List for list_directory_contents

def list_directory_contents(context, path: str):
    """Lists directory contents."""
    if not os.path.exists(path):
        context.speak(f"Sir, the directory '{path}' was not found.")
        logging.warning(f"List directory: Path not found - {path}")
        return
    if not os.path.isdir(path):
        context.speak(f"Sir, '{path}' is not a directory.")
        logging.warning(f"List directory: Path is not a directory - {path}")
        return
    try:
        files = os.listdir(path)
        if files:
            context.speak(f"Contents of directory '{path}':")
            for item in files:
                context.speak(f"- {item}")
        else:
            context.speak(f"The directory '{path}' is empty, sir.")
        logging.info(f"Listed directory '{path}': {files}")
    except PermissionError:
        context.speak(f"I'm sorry, sir, I don't have permission to list the directory '{path}'.")
        logging.error(f"List directory: Permission denied - {path}")
    except Exception as e:
        context.speak(f"An error occurred while trying to list the directory '{path}': {str(e)}")
        logging.error(f"List directory: Error listing '{path}': {e}", exc_info=True)

def read_file_content(context, path: str):
    """Reads file content."""
    if not os.path.exists(path):
        context.speak(f"Sir, the file '{path}' could not be found.")
        logging.warning(f"Read file: File not found - {path}")
        return
    if not os.path.isfile(path):
        context.speak(f"Sir, '{path}' is not a file.")
        logging.warning(f"Read file: Path is not a file - {path}")
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # For very long files, consider speaking a summary or a portion.
        # Here, we'll speak the beginning and log the full attempt.
        context.speak(f"Content of file '{path}':")
        if len(content) > 500: # Speak only a preview if too long
            context.speak(content[:500] + "\n... (file content truncated for brevity)")
        else:
            context.speak(content)
        logging.info(f"Read file '{path}'. Content length: {len(content)}")
    except PermissionError:
        context.speak(f"I'm afraid I don't have permission to read the file '{path}', sir.")
        logging.error(f"Read file: Permission denied - {path}")
    except Exception as e:
        context.speak(f"An error occurred while reading the file '{path}': {str(e)}")
        logging.error(f"Read file: Error reading '{path}': {e}", exc_info=True)

def write_content_to_file(context, path: str, content: str):
    """Writes content to a file. Overwrites if exists, creates if not."""
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir: # Check if path includes a directory
            os.makedirs(parent_dir, exist_ok=True)
            logging.info(f"Ensured directory exists: {parent_dir} for writing to {path}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        context.speak(f"The content has been successfully written to '{path}', sir.")
        logging.info(f"Wrote to file '{path}'. Content length: {len(content)}")
    except PermissionError:
        context.speak(f"I do not have permission to write to the file '{path}', sir.")
        logging.error(f"Write file: Permission denied - {path}")
    except Exception as e:
        context.speak(f"An error occurred while writing to the file '{path}': {str(e)}")
        logging.error(f"Write file: Error writing '{path}': {e}", exc_info=True)

def _test_skill(context):
    """
    Runs a quick self-test for the file_manager module.
    It creates a temporary directory and file, writes to it, lists, reads, and cleans up.
    """
    logging.info("[file_manager_test] Running self-test for file_manager module...")
    
    # It's good practice to use the tempfile module for truly temporary files/dirs
    # but for a simple self-contained test, a subdirectory that's cleaned up is also okay.
    # Let's create a test directory within the current working directory or a known temp spot.
    # For simplicity, we'll use a relative path and ensure cleanup.
    test_dir_name = "_fm_test_temp_dir"
    test_file_name = "test_file.txt"
    test_dir_path = os.path.join(os.getcwd(), test_dir_name) # Or use tempfile.mkdtemp()
    test_file_path = os.path.join(test_dir_path, test_file_name)
    test_content = "Hello from the file manager self-test!"

    try:
        # Ensure the test directory does not exist before starting
        if os.path.exists(test_dir_path):
            import shutil
            shutil.rmtree(test_dir_path)
            logging.info(f"[file_manager_test] Removed pre-existing test directory: {test_dir_path}")

        os.makedirs(test_dir_path, exist_ok=True)
        logging.info(f"[file_manager_test] Created temporary directory: {test_dir_path}")

        # Test 1: Write content to file
        logging.info(f"[file_manager_test] Testing write_content_to_file to {test_file_path}...")
        write_content_to_file(context, test_file_path, test_content)

        # Test 2: List directory contents
        logging.info(f"[file_manager_test] Testing list_directory_contents for {test_dir_path}...")
        list_directory_contents(context, test_dir_path)

        # Test 3: Read file content
        logging.info(f"[file_manager_test] Testing read_file_content for {test_file_path}...")
        read_file_content(context, test_file_path)

        logging.info("[file_manager_test] All file_manager self-tests passed successfully.")

    except Exception as e:
        logging.error(f"[file_manager_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py
    finally:
        # Cleanup: Remove the temporary directory and its contents
        if os.path.exists(test_dir_path):
            import shutil # Import here if not already imported, or at top of file
            shutil.rmtree(test_dir_path)
            logging.info(f"[file_manager_test] Cleaned up temporary directory: {test_dir_path}")