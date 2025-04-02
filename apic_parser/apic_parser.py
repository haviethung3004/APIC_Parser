import ijson
import json

def build_nested_object(parser):
    stack = []
    result = None
    
    for prefix, event, value in parser:
        if event == 'start_map':  # Entering an object
            new_dict = {}
            if stack:
                parent = stack[-1]
                if isinstance(parent, dict):
                    key = prefix.split('.')[-1] if '.' in prefix else prefix
                    parent[key] = new_dict
                elif isinstance(parent, list):
                    parent.append(new_dict)
            stack.append(new_dict)
            if result is None:
                result = new_dict
        elif event == 'start_array':  # Entering an array
            new_array = []
            if stack:
                parent = stack[-1]
                if isinstance(parent, dict):
                    key = prefix.split('.')[-1] if '.' in prefix else prefix
                    parent[key] = new_array
            stack.append(new_array)
        elif event == 'end_map' or event == 'end_array':  # Leaving an object or array
            stack.pop()
        elif event in ('string', 'number', 'boolean', 'null'):  # Leaf value
            if stack:
                parent = stack[-1]
                if isinstance(parent, dict):
                    key = prefix.split('.')[-1]
                    parent[key] = value
                elif isinstance(parent, list):
                    parent.append(value)
    return result

def find_object_by_name_iterative(data, object_type, name):
    """
    Find an object by its type (e.g., 'fvBD') and name (e.g., 'BD_484') using an iterative stack-based approach.
    Returns the full object as it appears in the original JSON, or None if not found.
    """
    # Stack holds tuples of (object, key) to explore
    stack = [(data, None)]  # Start with the root object, no key yet
    
    while stack:
        current_obj, parent_key = stack.pop()  # Get the next object to check
        
        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                # Check if this is the target object
                if key == object_type and "attributes" in value:
                    if value["attributes"].get("name") == name:
                        return {key: value}  # Found it, return the full object
                # Add nested dictionaries to the stack
                stack.append((value, key))
        
        elif isinstance(current_obj, list):
            # Add each item in the list to the stack
            for item in current_obj:
                stack.append((item, None))  # No key for list items
    
    return None  # Not found

if __name__ == "__main__":
    # Parse the JSON file
    with open(r'C:\Users\dsu979\Documents\APIC\APIC_Parser\tn-Datacenter1.json', 'rb') as file:
        parser = ijson.parse(file)
        nested_object = build_nested_object(parser)

    # Find the specific fvBD object with name "BD_484"
    target_object = find_object_by_name_iterative(nested_object, "fvAp", "BD_484")
    if target_object:
        print(json.dumps(target_object, indent=2))
    else:
        print(f"Object 'fvBD' with name 'BD_484' not found.")