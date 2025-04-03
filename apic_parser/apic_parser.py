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

def get_top_level_objects(data):
    """
    Get the top-level objects from the tenant data
    """
    top_level = []
    try:
        for item in data["imdata"]:
            if "fvTenant" in item:
                children = item["fvTenant"].get("children", [])
                for child in children:
                    for key, value in child.items():
                        if key not in top_level:
                            top_level.append({
                                key: value.get("attributes", {}).get("name", None),
                                "children": [None if "children" not in value else "[]"]
                            })
    except KeyError:
        return []
    return top_level

def has_nested_children(obj):
    """
    Check if the object has nested children
    """
    for key, value in obj.items():
        if isinstance(value, dict) and "children" in value:
            return True, value["children"]
    return False, None



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

def save_to_json(file_path, data):
    """Save the given data to a JSON file at the specified file path."""
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

if __name__ == "__main__":
    # Parse the JSON file
    with open(r'C:\Users\dsu979\Documents\APIC\APIC_Parser\tn-Datacenter1.json', 'rb') as file:
        parser = ijson.parse(file)
        nested_object = build_nested_object(parser)

        #Save this content
        # save_to_json(r'C:\Users\dsu979\Documents\APIC\APIC_Parser\nested_object.json', nested_object)

        # Get the top-level objects
        top_level_objects = get_top_level_objects(nested_object)
        for child in top_level_objects:
            for key, value in child.items():
                print(f"Object: {key}, Name: {value}")

