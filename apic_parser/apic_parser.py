import ijson
import json
import os
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)


def build_nested_object(file_path):
    """
    Build a nested Python object from an APIC JSON file using streaming parser.
    
    Args:
        file_path (str): Path to the APIC JSON file to parse.
        
    Returns:
        dict: The parsed nested object representation of the JSON file.
    """
    logger.info(f"Parsing file: {file_path}")
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
        logger.info(f"Successfully parsed file: {file_path}")
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
    
    logger.info(f"Searching for objects of type '{object_type}' with names: {', '.join(names_list)}")

    while stack:
        current_obj, _ = stack.pop()

        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                if key == object_type and isinstance(value, dict) and "attributes" in value:
                    # Check if name is in the list/set of requested names
                    object_actual_name = value.get("attributes", {}).get("name")
                    if object_actual_name is not None and object_actual_name in names_set:
                        logger.debug(f"Found a match: '{object_actual_name}'")
                        found_objects.append({key: value})
                        # Continue searching for other matches

                # Keep exploring deeper in the hierarchy
                if isinstance(value, (dict, list)):
                    stack.append((value, key))

        elif isinstance(current_obj, list):
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))

    logger.info(f"Found {len(found_objects)} matching object(s).")
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
    
    logger.info(f"Searching for object of type '{object_type}' with name '{name}'")
    
    while stack:
        current_obj, parent_key = stack.pop()  # Get the next object to check
        
        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                # Check if this is the target object
                if key == object_type and "attributes" in value:
                    if value["attributes"].get("name") == name:
                        logger.debug(f"Found a match: '{name}'")
                        return {key: value}  # Found it, return the full object
                # Add nested dictionaries to the stack
                if isinstance(value, (dict, list)):
                    stack.append((value, key))
        
        elif isinstance(current_obj, list):
            # Add each item in the list to the stack
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))  # No key for list items
    
    logger.info(f"No object of type '{object_type}' with name '{name}' found.")
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
        logger.warning(f"Could not extract tenant information from nested_object.json: {e}")
    
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
                            logger.info(f"Set status '{status_value}' for {obj_type} '{obj_name}'")
                            
    return results


def find_ap_and_children_by_name(data, ap_name):
    """
    Find an Application Profile (fvAp) by name along with all its nested children structure.
    
    Args:
        data (dict): The nested dictionary/list structure to search within.
        ap_name (str): The name of the Application Profile to find.
        
    Returns:
        dict: The found Application Profile with all its nested children, or None if not found.
    """
    # Stack holds tuples of (object, key) to explore
    stack = [(data, None)]  # Start with the root object, no key yet
    
    logger.info(f"Searching for Application Profile with name '{ap_name}'")
    
    while stack:
        current_obj, parent_key = stack.pop()  # Get the next object to check
        
        if isinstance(current_obj, dict):
            for key, value in current_obj.items():
                # Check if this is an Application Profile
                if key == "fvAp" and "attributes" in value:
                    if value["attributes"].get("name") == ap_name:
                        logger.debug(f"Found Application Profile: '{ap_name}'")
                        return {key: value}  # Found it, return the full object with children
                # Add nested dictionaries to the stack
                if isinstance(value, (dict, list)):
                    stack.append((value, key))
        
        elif isinstance(current_obj, list):
            # Add each item in the list to the stack
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))  # No key for list items
    
    logger.info(f"No Application Profile with name '{ap_name}' found.")
    return None  # Not found


def get_nested_epgs_from_ap(ap_data):
    """
    Extract all EPGs (fvAEPg) from an Application Profile structure.
    
    Args:
        ap_data (dict): The Application Profile data structure with its children.
        
    Returns:
        list: A list of dictionaries containing EPG objects.
    """
    epgs = []
    
    if not ap_data or "fvAp" not in ap_data:
        return epgs
        
    # Navigate to the children of the AP
    ap_children = ap_data["fvAp"].get("children", [])
    
    # Find all EPGs in the children
    for child in ap_children:
        if "fvAEPg" in child:
            epgs.append(child)
    
    return epgs


def set_status_for_nested_objects(results, object_paths, status_type):
    """
    Set the status attribute for specific objects in the results including nested objects.
    Supports setting status for objects identified by paths like "fvAp:AppName/fvAEPg:EpgName"
    
    Args:
        results (dict): The formatted APIC results dictionary
        object_paths (list): List of object paths to update (e.g., ["fvAp:WebApp", "fvAp:WebApp/fvAEPg:WebEPG"])
        status_type (str): Status to set - either 'create' or 'delete'
        
    Returns:
        dict: Updated results with status attributes set on specified objects
    """
    if not results or "imdata" not in results or not results["imdata"]:
        return results
        
    status_value = "deleted" if status_type == "delete" else "created,modified"
    
    # Organize paths by their structure
    top_level_paths = []
    nested_paths = {}
    
    for path in object_paths:
        path_parts = path.split("/")
        if len(path_parts) == 1:
            # This is a top-level object (e.g., "fvAp:WebServer")
            top_level_paths.append(path)
        else:
            # This is a nested path (e.g., "fvAp:WebServer/fvAEPg:EPG_123")
            root_part = path_parts[0]
            if root_part not in nested_paths:
                nested_paths[root_part] = []
            nested_paths[root_part].append(path_parts[1:])
    
    # Process each tenant
    for tenant in results["imdata"]:
        if "fvTenant" in tenant and "children" in tenant["fvTenant"]:
            tenant_children = tenant["fvTenant"]["children"]
            
            # First process all top-level paths
            for path in top_level_paths:
                if ":" in path:
                    obj_type, obj_name = path.split(":")
                    
                    # Look for the top-level object
                    for child in tenant_children:
                        if obj_type in child and "attributes" in child[obj_type]:
                            if child[obj_type]["attributes"].get("name") == obj_name:
                                # Set status on the top-level object
                                child[obj_type]["attributes"]["status"] = status_value
                                logger.info(f"Set status '{status_value}' for {obj_type} '{obj_name}'")
                                break
            
            # Then process all nested paths
            for root_path, child_paths in nested_paths.items():
                if ":" in root_path:
                    obj_type, obj_name = root_path.split(":")
                    
                    # Find the parent object
                    for child in tenant_children:
                        if obj_type in child and "attributes" in child[obj_type]:
                            if child[obj_type]["attributes"].get("name") == obj_name:
                                # We found the parent, now process its children
                                # Note: We do NOT set status on the parent for nested paths
                                if "children" in child[obj_type]:
                                    for nested_path in child_paths:
                                        _process_nested_path_only(child[obj_type]["children"], nested_path, status_value)
                                break
    
    return results


def _process_nested_path_only(children, path_parts, status_value):
    """
    Helper function to process nested paths for setting status attributes
    without modifying parent objects.
    
    Args:
        children (list): The children array to search through
        path_parts (list): Remaining parts of the object path
        status_value (str): Status value to set
    """
    if not path_parts or not children:
        return
        
    # Get the current part to process
    if ":" in path_parts[0]:
        obj_type, obj_name = path_parts[0].split(":")
        
        # Look for the object in children
        for child in children:
            if obj_type in child and "attributes" in child[obj_type]:
                if child[obj_type]["attributes"].get("name") == obj_name:
                    # Set status on this object
                    child[obj_type]["attributes"]["status"] = status_value
                    logger.info(f"Set status '{status_value}' for {obj_type} '{obj_name}'")
                    
                    # Continue with next level if exists
                    if len(path_parts) > 1 and "children" in child[obj_type]:
                        _process_nested_path_only(child[obj_type]["children"], path_parts[1:], status_value)
                    
                    break


def get_ap_and_epg_names(data):
    """
    Get all Application Profiles and their EPGs from the data.
    
    Args:
        data (dict): The nested object data structure
        
    Returns:
        dict: A dictionary where keys are AP names and values are lists of their EPG names
    """
    ap_epg_dict = {}
    stack = [(data, None)]
    
    while stack:
        current_obj, _ = stack.pop()
        
        if isinstance(current_obj, dict):
            # Check if this is an Application Profile
            if "fvAp" in current_obj and "attributes" in current_obj["fvAp"]:
                ap_name = current_obj["fvAp"]["attributes"].get("name")
                if ap_name:
                    ap_epg_dict[ap_name] = []
                    
                    # Look for EPGs in this AP's children
                    if "children" in current_obj["fvAp"]:
                        for child in current_obj["fvAp"]["children"]:
                            if "fvAEPg" in child and "attributes" in child["fvAEPg"]:
                                epg_name = child["fvAEPg"]["attributes"].get("name")
                                if epg_name:
                                    ap_epg_dict[ap_name].append(epg_name)
            
            # Continue searching deeper
            for key, value in current_obj.items():
                if isinstance(value, (dict, list)):
                    stack.append((value, key))
                    
        elif isinstance(current_obj, list):
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    stack.append((item, None))
    
    return ap_epg_dict


if __name__ == "__main__":
    # Setup logging when running this module directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
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
                logger.info(f"Object: {key}, Name: {value}")

