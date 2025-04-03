import ijson
import json


def has_nested_children(obj):
    """
    Check if the object has nested children
    """
    for key, value in obj.items():
        if isinstance(value, dict) and "children" in value:
            return True, value["children"]
    return False, None


def build_nested_object(file_path):

    with open(file_path, 'rb') as file:
        parser = ijson.parse(file)

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
                                "children": [None if "children" not in value else value["children"]]
                            })
    except KeyError:
        return []
    return top_level




def find_all_objects_by_name_iterative(data, object_type, names_list):
    """
    Find ALL objects matching the type (key) and ANY of the names
    provided in the names_list (in attributes). Uses an iterative DFS.

    Args:
        data: The nested dictionary/list structure to search within.
        object_type (str): The dictionary key identifying the object type (e.g., 'fvBD').
        names_list (list): A list of strings, where each string is a potential 'name'
                           attribute value to match (e.g., ['BD_484', 'BD791']).

    Returns:
        list: A list containing all matching objects found [{key: value}, ...].
              Returns an empty list ([]) if no matches are found.
    """
    found_objects = []
    stack = [(data, None)]

    # Make the names_list a set for potentially faster 'in' checks, especially with many names
    names_set = set(names_list)

    # print(f"Searching for ALL objects: Type='{object_type}', Name(s) in {names_set}")

    while stack:
        current_obj, _ = stack.pop()

        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                if key == object_type and isinstance(value, dict) and "attributes" in value:
                    # --- CHANGE HERE: Check if name is IN the list/set ---
                    object_actual_name = value.get("attributes", {}).get("name")
                    # Check if the actual name exists and is one of the names we're looking for
                    if object_actual_name is not None and object_actual_name in names_set:
                        print(f"  -> Found a match: Key='{key}', Name='{object_actual_name}'. Adding to results.")
                        found_objects.append({key: value})
                        # Continue searching

                # Keep Digging Deeper
                if isinstance(value, (dict, list)):
                    stack.append((value, key))

        elif isinstance(current_obj, list):
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))

    # print(f"Search complete. Found {len(found_objects)} matching object(s).")
    return found_objects

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

def format_result_in_apic_standard(result):
    """
    Format the result in the standard APIC format with totalCount and imdata structure.
    Wraps the result(s) in an fvTenant structure, preserving the original tenant attributes.
    
    Args:
        result: The found object, a list of objects, or None if not found
    
    Returns:
        A dictionary in standard APIC format with the result(s) wrapped in fvTenant and imdata
    """
    if result is None:
        return {
            "totalCount": "0",
            "imdata": []
        }
    
    # Convert single result to a list for uniform handling
    results_list = result if isinstance(result, list) else [result]
    
    # Filter out any None values
    results_list = [r for r in results_list if r is not None]
    
    if not results_list:
        return {
            "totalCount": "0",
            "imdata": []
        }
    
    # Get tenant information from the original data
    tenant_info = None
    try:
        with open(r'C:\Users\dsu979\Documents\APIC\APIC_Parser\nested_object.json', 'r') as f:
            import json
            original_data = json.load(f)
            if "imdata" in original_data and len(original_data["imdata"]) > 0:
                if "fvTenant" in original_data["imdata"][0]:
                    # Extract tenant attributes from original file
                    tenant_info = original_data["imdata"][0]["fvTenant"]["attributes"]
    except Exception as e:
        print(f"Warning: Could not extract tenant information from nested_object.json: {e}")
    
    # Create default tenant attributes if we couldn't get them from the file
    if tenant_info is None:
        tenant_info = {
            "name": "Datacenter1",
            "status": "created,modified"
        }
    
    # Create fvTenant wrapper with children containing all results
    tenant_wrapper = {
        "fvTenant": {
            "attributes": tenant_info,
            "children": results_list
        }
    }
    
    return {
        "totalCount": '1',
        "imdata": [tenant_wrapper]
    }

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

