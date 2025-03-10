"""
Core extraction functionality for APIC configuration files
"""

class ACIObjectExtractor:
    """Class to extract and process objects from ACI configuration"""
    
    @staticmethod
    def extract_object(node, target_class, result=None):
        """
        Extract objects of a specific class from the configuration
        
        Args:
            node: Current node to process
            target_class: The class name to extract
            result: Result list to populate (initialized on first call)
            
        Returns:
            List of matching objects with their attributes and children
        """
        if result is None:
            result = []
        
        # If node is a list, process each item
        if isinstance(node, list):
            for item in node:
                ACIObjectExtractor.extract_object(item, target_class, result)
            return result
            
        # Process dictionary objects
        if isinstance(node, dict):
            for class_name, value in node.items():
                if isinstance(value, dict):
                    # If this node matches the target class, add to results
                    if class_name == target_class:
                        attributes = value.get('attributes', {})

                        entry = {
                            "class": class_name,
                            "attributes": attributes,
                            "children": []
                        }
                        result.append(entry)
                        
                        # Add all children regardless of class
                        children = value.get('children', [])
                        if children:
                            for child in children:
                                for child_class, child_value in child.items():
                                    child_entry = {
                                        "class": child_class,
                                        "attributes": child_value.get('attributes', {}),
                                        "children": []
                                    }
                                    
                                    # Recursively extract children of this child
                                    if child_value.get('children'):
                                        # Extract all children recursively regardless of class
                                        child_children = []
                                        for grandchild in child_value.get('children'):
                                            for gc_class, gc_value in grandchild.items():
                                                gc_entry = {
                                                    "class": gc_class,
                                                    "attributes": gc_value.get('attributes', {}),
                                                    "children": []
                                                }
                                                # Process deeper children if they exist
                                                if gc_value.get('children'):
                                                    ACIObjectExtractor.extract_object(gc_value.get('children'), None, gc_entry['children'])
                                                child_children.append(gc_entry)
                                        
                                        child_entry['children'] = child_children
                                    
                                    entry['children'].append(child_entry)
                    else:
                        # Recursively process children even if current class doesn't match
                        children = value.get('children', [])
                        if children:
                            for child in children:
                                ACIObjectExtractor.extract_object(child, target_class, result)
        
        return result

    @staticmethod
    def extract_all_objects(node, parent_path="", result=None):
        """
        Extract all objects from the configuration regardless of class
        
        Args:
            node: Current node to process
            parent_path: Path in object hierarchy (for tracking/debugging)
            result: List to collect results (initialized on first call)
            
        Returns:
            List of objects with their attributes and children
        """
        if result is None:
            result = []
            
        # Handle lists - process each item
        if isinstance(node, list):
            for i, item in enumerate(node):
                current_path = f"{parent_path}[{i}]"
                ACIObjectExtractor.extract_all_objects(item, current_path, result)
            return result
        
        # Handle dictionaries - this is where we extract object data
        if isinstance(node, dict):
            # Check if this is an ACI object (usually has one key with attributes & children)
            for class_name, data in node.items():
                if isinstance(data, dict) and ('attributes' in data or 'children' in data):
                    # This looks like an ACI object
                    current_path = f"{parent_path}/{class_name}"
                    attributes = data.get('attributes', {})
                    
                    # Create entry for this object
                    obj_entry = {
                        "class": class_name,
                        "path": current_path,
                        "attributes": attributes,
                        "children": []
                    }
                    
                    # Add to result list
                    result.append(obj_entry)
                    
                    # Process children recursively
                    children = data.get('children', [])
                    if children:
                        child_results = []
                        ACIObjectExtractor.extract_all_objects(children, current_path, child_results)
                        obj_entry['children'] = child_results
                else:
                    # This is a regular dictionary, just process recursively
                    ACIObjectExtractor.extract_all_objects(data, f"{parent_path}/{class_name}", result)
        
        return result

    @staticmethod
    def get_child_original_config(config, parent_index=0, child_index=None):
        """
        Get the original configuration of a specific child by index
        
        Args:
            config: The loaded JSON configuration
            parent_index: Index of the parent object (default is 0, typically imdata[0])
            child_index: Index of the child to extract (0-based)
            
        Returns:
            The original child object configuration as a dictionary, or None if not found
        """
        try:
            # Navigate to the main tenant object (typically first object in imdata)
            if 'imdata' in config and isinstance(config['imdata'], list):
                parent_obj = config['imdata'][parent_index]
                
                # Get the first key in the parent object (typically 'fvTenant')
                if parent_obj:
                    parent_class = list(parent_obj.keys())[0]
                    
                    # If a specific child index is requested
                    if child_index is not None:
                        if 'children' in parent_obj[parent_class]:
                            children = parent_obj[parent_class]['children']
                            if 0 <= child_index < len(children):
                                return children[child_index]
                            else:
                                print(f"Child index {child_index} out of range (0-{len(children)-1})")
                    else:
                        # Return all children
                        if 'children' in parent_obj[parent_class]:
                            return parent_obj[parent_class]['children']
        except Exception as e:
            print(f"Error extracting child configuration: {e}")
        
        return None

    @staticmethod
    def set_object_status(config, status_value, object_path=None):
        """
        Set the status attribute for an object or all objects in the configuration
        
        Args:
            config: The ACI configuration object (can be full config or a specific object)
            status_value: Status value to set (e.g. "created", "modified, created", "deleted")
            object_path: Path to specific object to update (if None, updates root object)
            
        Returns:
            The modified configuration with status attributes added/updated
        """
        if not config:
            return config
            
        # Handle different config structures
        if isinstance(config, dict):
            # If it's a single-class ACI object format (e.g., {"fvAp": {...}})
            if len(config) == 1 and isinstance(list(config.values())[0], dict):
                class_name = list(config.keys())[0]
                class_data = config[class_name]
                
                # Initialize attributes dict if it doesn't exist
                if "attributes" not in class_data:
                    class_data["attributes"] = {}
                    
                # Set the status attribute
                class_data["attributes"]["status"] = status_value
                
                # If this is the target object, we're done
                # Otherwise, recursively process all children too
                if object_path and len(object_path) > 1:
                    # Remove the first path component and continue with children
                    next_path = object_path[1:]
                    if "children" in class_data and isinstance(class_data["children"], list):
                        for child in class_data["children"]:
                            ACIObjectExtractor.set_object_status(child, status_value, next_path)
            
            # Handle "imdata" format of configurations
            elif "imdata" in config and isinstance(config["imdata"], list):
                for item in config["imdata"]:
                    ACIObjectExtractor.set_object_status(item, status_value, 
                                                      object_path[0] if object_path else None)
        
        # Handle list format (like children arrays)
        elif isinstance(config, list):
            # If object_path is provided, find the specific object to update
            if object_path:
                target_class = object_path[0]
                for item in config:
                    if isinstance(item, dict) and len(item) == 1:
                        class_name = list(item.keys())[0]
                        if class_name == target_class:
                            # Found target, update it
                            next_path = object_path[1:] if len(object_path) > 1 else None
                            ACIObjectExtractor.set_object_status(item, status_value, next_path)
            else:
                # No path provided, update all items in list
                for item in config:
                    ACIObjectExtractor.set_object_status(item, status_value, None)
                    
        return config
        
    @staticmethod
    def set_status_for_child(config, child_index, status_value):
        """
        Set the status for a specific child by index
        
        Args:
            config: The loaded ACI configuration
            child_index: Index of the child to update (0-based)
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the child configuration
            child = ACIObjectExtractor.get_child_original_config(config, 0, child_index)
            if not child:
                return False
                
            # Set the status
            ACIObjectExtractor.set_object_status(child, status_value)
            return True
        except Exception as e:
            print(f"Error setting status for child: {e}")
            return False