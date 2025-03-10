"""
Utility functions for file operations
"""
import json
import os

def load_json_config(file_path):
    """
    Load JSON configuration from file
    
    Args:
        file_path: Path to the JSON configuration file
        
    Returns:
        Parsed JSON data as Python dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        return json.load(f)
        
def save_json_config(data, file_path):
    """
    Save JSON data to a file with pretty formatting
    
    Args:
        data: The Python dictionary to save as JSON
        file_path: Path where to save the JSON file
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        OSError: If directory creation fails
    """
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON data: {e}")
        return False