"""
Utility functions for file operations
"""
import json
import os
import ijson  # For memory-efficient JSON parsing

def load_json_config(file_path, use_streaming=True):
    """
    Load JSON configuration from file with memory optimization
    
    Args:
        file_path: Path to the JSON configuration file
        use_streaming: If True, use streaming parser for large files
        
    Returns:
        Parsed JSON data as Python dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    # Check file size to determine parsing method
    file_size = os.path.getsize(file_path)
    
    if use_streaming and file_size > 10 * 1024 * 1024:  # Use streaming for files > 10MB
        try:
            with open(file_path, 'rb') as f:
                # Use ijson for memory-efficient parsing of large files
                parser = ijson.parse(f)
                data = {}
                current_path = []
                current_obj = None
                
                for prefix, event, value in parser:
                    if prefix == '' and event == 'map_key':
                        current_path = [value]
                        if current_obj is None:
                            current_obj = {}
                            data[value] = current_obj
                    elif len(current_path) > 0:
                        if event == 'map_key':
                            current_path.append(value)
                        elif event in ('string', 'number', 'boolean', 'null'):
                            # Navigate to the correct nested position
                            target = data
                            for key in current_path[:-1]:
                                if key not in target:
                                    target[key] = {}
                                target = target[key]
                            target[current_path[-1]] = value
                            current_path.pop()
                
                return data
        except ImportError:
            # Fall back to standard json if ijson is not available
            pass
    
    # Use standard json for smaller files or if streaming failed
    with open(file_path, 'r', buffering=65536) as f:  # Use 64KB buffer
        return json.load(f)
        
def save_json_config(data, file_path, chunk_size=8192):
    """
    Save JSON data to a file with memory-efficient streaming
    
    Args:
        data: The Python dictionary to save as JSON
        file_path: Path where to save the JSON file
        chunk_size: Size of chunks for streaming write
        
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
            
        with open(file_path, 'w', buffering=chunk_size) as f:
            # Use compact encoding for arrays/objects to reduce memory usage
            for chunk in json.JSONEncoder(indent=2).iterencode(data):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error saving JSON data: {e}")
        return False