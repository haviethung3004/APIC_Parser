import ijson
import json
import os



def build_nested_object(file_path):
    """
    Build a nested Python object from an APIC JSON file using streaming parser.
    
    Args:
        file_path (str): Path to the APIC JSON file to parse.
        
    Returns:
        dict: The parsed nested object representation of the JSON file.
    """
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
    Get the top-level objects from the tenant data.
    
    Args:
        data (dict): The nested object data structure built from the APIC JSON file.
        
    Returns:
        list: A list of dictionaries representing the top-level objects in the tenant.
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
    provided in the names_list (in attributes). Uses an iterative DFS approach.

    Args:
        data (dict): The nested dictionary/list structure to search within.
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
    
    print(f"Searching for objects of type '{object_type}' with names: {', '.join(names_list)}")

    while stack:
        current_obj, _ = stack.pop()

        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                if key == object_type and isinstance(value, dict) and "attributes" in value:
                    # Check if name is in the list/set of requested names
                    object_actual_name = value.get("attributes", {}).get("name")
                    if object_actual_name is not None and object_actual_name in names_set:
                        print(f"  -> Found a match: '{object_actual_name}'")
                        found_objects.append({key: value})
                        # Continue searching for other matches

                # Keep exploring deeper in the hierarchy
                if isinstance(value, (dict, list)):
                    stack.append((value, key))

        elif isinstance(current_obj, list):
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))

    print(f"Found {len(found_objects)} matching object(s).")
    return found_objects


def find_object_by_name_iterative(data, object_type, name):
    """
    Find a single object by its type and name using an iterative stack-based approach.
    
    Args:
        data (dict): The nested dictionary/list structure to search within.
        object_type (str): The dictionary key identifying the object type (e.g., 'fvBD').
        name (str): The name attribute value to match (e.g., 'BD_484').
        
    Returns:
        dict: The found object as it appears in the original JSON, or None if not found.
    """
    # Stack holds tuples of (object, key) to explore
    stack = [(data, None)]  # Start with the root object, no key yet
    
    print(f"Searching for object of type '{object_type}' with name '{name}'")
    
    while stack:
        current_obj, parent_key = stack.pop()  # Get the next object to check
        
        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                # Check if this is the target object
                if key == object_type and "attributes" in value:
                    if value["attributes"].get("name") == name:
                        print(f"  -> Found a match: '{name}'")
                        return {key: value}  # Found it, return the full object
                # Add nested dictionaries to the stack
                if isinstance(value, (dict, list)):
                    stack.append((value, key))
        
        elif isinstance(current_obj, list):
            # Add each item in the list to the stack
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))  # No key for list items
    
    print(f"No object of type '{object_type}' with name '{name}' found.")
    return None  # Not found


def get_tenant_info():
    """
    Get tenant information from the nested_object.json file.
    
    Returns:
        dict: The tenant attributes, or default values if the file can't be read.
    """
    # Default tenant info if we can't get it from the file
    default_tenant_info = {
        "name": "Datacenter1",
        "status": "created,modified"
    }
    
    try:
        nested_object_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nested_object.json')
        with open(nested_object_path, 'r') as f:
            original_data = json.load(f)
            if "imdata" in original_data and len(original_data["imdata"]) > 0:
                if "fvTenant" in original_data["imdata"][0]:
                    # Extract tenant attributes from original file
                    tenant_info = original_data["imdata"][0]["fvTenant"]["attributes"]
                    return tenant_info
    except Exception as e:
        print(f"Warning: Could not extract tenant information from nested_object.json: {e}")
    
    return default_tenant_info


def format_result_in_apic_standard(result):
    """
    Format the result in the standard APIC format with totalCount and imdata structure.
    Wraps the result(s) in an fvTenant structure, preserving the original tenant attributes.
    
    Args:
        result: The found object, a list of objects, or None if not found
    
    Returns:
        dict: A dictionary in standard APIC format with the result(s) wrapped in fvTenant and imdata
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
    tenant_info = get_tenant_info()
    
    # Create fvTenant wrapper with children containing all results
    tenant_wrapper = {
        "fvTenant": {
            "attributes": tenant_info,
            "children": results_list
        }
    }
    
    return {
        "totalCount": str(len(results_list)),
        "imdata": [tenant_wrapper]
    }


def save_to_json(file_path, data):
    """
    Save the given data to a JSON file at the specified file path.
    
    Args:
        file_path (str): The path where the JSON file should be saved.
        data (dict): The data to be saved as JSON.
    """
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)


def set_object_status(results, object_names, status_type):
    """
    Set the status attribute for specific objects in the results.
    
    Args:
        results (dict): The formatted APIC results dictionary
        object_names (list): List of object names to update (e.g., ['BD_484', 'BD_721'])
        status_type (str): Status to set - either 'create' or 'delete'
        
    Returns:
        dict: Updated results with status attributes set
    """
    if not results or "imdata" not in results or not results["imdata"]:
        return results
        
    status_value = "deleted" if status_type == "delete" else "created,modified"
    names_set = set(object_names)
    
    # Loop through each tenant
    for tenant in results["imdata"]:
        if "fvTenant" in tenant and "children" in tenant["fvTenant"]:
            # Loop through each child object in the tenant
            for child in tenant["fvTenant"]["children"]:
                # Get the first key (object type)
                for obj_type, obj_data in child.items():
                    # Check if this is an object we want to update
                    if "attributes" in obj_data and "name" in obj_data["attributes"]:
                        obj_name = obj_data["attributes"]["name"]
                        if obj_name in names_set:
                            # Set the status attribute
                            obj_data["attributes"]["status"] = status_value
                            print(f"Set status '{status_value}' for {obj_type} '{obj_name}'")
                            
    return results


if __name__ == "__main__":
    # Example usage when running the module directly
    import os
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, 'tn-Datacenter1.json')
    
    nested_object = build_nested_object(file_path)

    # Optional: Save the parsed object to nested_object.json
    # save_to_json(os.path.join(base_dir, 'nested_object.json'), nested_object)

    # Get the top-level objects
    top_level_objects = get_top_level_objects(nested_object)
    for child in top_level_objects:
        for key, value in child.items():
            if key != "children":
                print(f"Object: {key}, Name: {value}")

