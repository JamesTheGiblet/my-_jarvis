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