"""
File handling utilities for the AI Report Quality Judge system.

This module provides functions to read and validate report files in various formats.
"""
import os
from typing import List, Optional, Tuple, Dict, Any, Union


def read_text_file(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Read content from a text file.
    
    Args:
        file_path: Path to the text file to read
        encoding: Character encoding of the file (default: utf-8)
        
    Returns:
        The content of the file as a string
        
    Raises:
        FileNotFoundError: If the specified file does not exist
        PermissionError: If the user lacks permission to read the file
        UnicodeDecodeError: If the file cannot be decoded with the specified encoding
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not os.path.isfile(file_path):
        raise ValueError(f"Path does not point to a file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read()
        return content
    except UnicodeDecodeError:
        raise UnicodeDecodeError(f"Could not decode file with {encoding} encoding. Please specify the correct encoding.")
    except PermissionError:
        raise PermissionError(f"Permission denied when trying to read {file_path}")
    except Exception as e:
        raise IOError(f"Error reading file {file_path}: {str(e)}")


def validate_file_type(file_path: str, allowed_extensions: List[str] = ['.txt', '.md']) -> bool:
    """
    Validate that a file has one of the allowed extensions.
    
    Args:
        file_path: Path to the file to validate
        allowed_extensions: List of allowed file extensions (with dot)
        
    Returns:
        True if the file has a valid extension, False otherwise
    """
    _, extension = os.path.splitext(file_path)
    return extension.lower() in [ext.lower() for ext in allowed_extensions]


def list_files_in_directory(directory_path: str, allowed_extensions: Optional[List[str]] = None) -> List[str]:
    """
    List all files in a directory (optionally filtered by extension).
    
    Args:
        directory_path: Path to the directory to scan
        allowed_extensions: Optional list of allowed file extensions to filter by
        
    Returns:
        List of file paths that match the criteria
        
    Raises:
        FileNotFoundError: If the directory does not exist
        NotADirectoryError: If the path exists but is not a directory
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"Path is not a directory: {directory_path}")
    
    file_paths = []
    
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        
        if os.path.isfile(file_path):
            if allowed_extensions is None or validate_file_type(file_path, allowed_extensions):
                file_paths.append(file_path)
    
    return file_paths


# Example usage
if __name__ == "__main__":
    try:
        # Demo file path - replace with an actual file for testing
        demo_file = "README.md"
        
        if os.path.exists(demo_file):
            # Read the file content
            content = read_text_file(demo_file)
            print(f"Successfully read file {demo_file}:")
            print(f"Character count: {len(content)}")
            print(f"First 200 characters: {content[:200]}...")
            
            # Validate file type
            is_valid = validate_file_type(demo_file, ['.md', '.txt'])
            print(f"\nFile has valid extension: {is_valid}")
        else:
            print(f"Demo file {demo_file} does not exist. Please create it or specify another file.")
    
    except Exception as e:
        print(f"Error during example usage: {e}") 