"""
Core extraction functionality for APIC configuration files
"""
from typing import Dict, List, Generator, Any, Optional
from functools import lru_cache

class ACIObjectExtractor:
    """Class to extract and process objects from ACI configuration"""
    
    _cache = {}  # Class-level cache for frequently accessed paths
    
    @staticmethod
    def _clear_cache():
        """Clear the internal cache"""
        ACIObjectExtractor._cache.clear()
    
    @staticmethod
    def _process_children(children: List[Dict], parent_path: str = "") -> Generator[Dict, None, None]:
        """Process children objects efficiently using a generator"""
        for i, child in enumerate(children):
            if isinstance(child, dict):
                for class_name, data in child.items():
                    current_path = f"{parent_path}/{class_name}[{i}]"
                    if isinstance(data, dict):
                        yield {
                            "class": class_name,
                            "path": current_path,
                            "attributes": data.get('attributes', {}),
                            "children": list(ACIObjectExtractor._process_nested_children(
                                data.get('children', []),
                                current_path
                            ))
                        }

    @staticmethod
    def _process_nested_children(children: List[Dict], parent_path: str) -> Generator[Dict, None, None]:
        """Process nested children efficiently"""
        yield from ACIObjectExtractor._process_children(children, parent_path)

    @staticmethod
    @lru_cache(maxsize=128)
    def extract_object(node: Dict, target_class: str) -> List[Dict]:
        """
        Extract objects of a specific class from the configuration
        
        Args:
            node: Current node to process
            target_class: The class name to extract
            
        Returns:
            List of matching objects with their attributes and children
        """
        result = []
        
        if isinstance(node, list):
            for item in node:
                result.extend(ACIObjectExtractor.extract_object(
                    tuple(item.items()) if isinstance(item, dict) else item,
                    target_class
                ))
            return result
            
        if isinstance(node, dict):
            for class_name, value in node.items():
                if isinstance(value, dict):
                    if class_name == target_class:
                        attributes = value.get('attributes', {})
                        children = value.get('children', [])
                        
                        result.append({
                            "class": class_name,
                            "attributes": attributes,
                            "children": list(ACIObjectExtractor._process_children(children))
                        })
                    else:
                        children = value.get('children', [])
                        if children:
                            result.extend(ACIObjectExtractor.extract_object(
                                children, target_class
                            ))
        
        return result

    @staticmethod
    def extract_all_objects(node: Dict, parent_path: str = "", batch_size: int = 1000) -> Generator[Dict, None, None]:
        """
        Extract all objects from the configuration using memory-efficient generator
        
        Args:
            node: Current node to process
            parent_path: Path in object hierarchy
            batch_size: Number of objects to process in each batch
            
        Returns:
            Generator yielding objects with their attributes and children
        """
        if isinstance(node, list):
            for i, item in enumerate(node):
                current_path = f"{parent_path}[{i}]"
                yield from ACIObjectExtractor.extract_all_objects(item, current_path)
        
        elif isinstance(node, dict):
            batch = []
            for class_name, data in node.items():
                if isinstance(data, dict) and ('attributes' in data or 'children' in data):
                    current_path = f"{parent_path}/{class_name}"
                    obj = {
                        "class": class_name,
                        "path": current_path,
                        "attributes": data.get('attributes', {}),
                        "children": []
                    }
                    
                    # Process children if they exist
                    children = data.get('children', [])
                    if children:
                        obj['children'] = list(ACIObjectExtractor._process_children(
                            children, current_path
                        ))
                    
                    batch.append(obj)
                    
                    # Yield batch when it reaches the specified size
                    if len(batch) >= batch_size:
                        yield from batch
                        batch = []
                else:
                    # Regular dictionary, process recursively
                    yield from ACIObjectExtractor.extract_all_objects(
                        data, f"{parent_path}/{class_name}"
                    )
            
            # Yield any remaining objects in the final batch
            if batch:
                yield from batch

    @staticmethod
    def get_child_original_config(config: Dict, parent_index: int = 0, child_index: Optional[int] = None) -> Optional[Dict]:
        """
        Get the original configuration of a specific child by index with caching
        
        Args:
            config: The loaded JSON configuration
            parent_index: Index of the parent object (default is 0)
            child_index: Index of the child to extract (0-based)
            
        Returns:
            The original child object configuration or None if not found
        """
        cache_key = (parent_index, child_index)
        if cache_key in ACIObjectExtractor._cache:
            return ACIObjectExtractor._cache[cache_key]
            
        try:
            if 'imdata' in config and isinstance(config['imdata'], list):
                parent_obj = config['imdata'][parent_index]
                if parent_obj:
                    parent_class = list(parent_obj.keys())[0]
                    
                    if child_index is not None:
                        if 'children' in parent_obj[parent_class]:
                            children = parent_obj[parent_class]['children']
                            if 0 <= child_index < len(children):
                                result = children[child_index]
                                ACIObjectExtractor._cache[cache_key] = result
                                return result
                            print(f"Child index {child_index} out of range (0-{len(children)-1})")
                    else:
                        if 'children' in parent_obj[parent_class]:
                            result = parent_obj[parent_class]['children']
                            ACIObjectExtractor._cache[cache_key] = result
                            return result
        except Exception as e:
            print(f"Error extracting child configuration: {e}")
        
        return None

    @staticmethod
    def set_object_status(config: Dict, status_value: Optional[str], object_path: Optional[List[str]] = None) -> Dict:
        """
        Set the status attribute for an object efficiently
        
        Args:
            config: The ACI configuration object
            status_value: Status value to set or None to remove status
            object_path: Path to specific object to update
            
        Returns:
            The modified configuration
        """
        def update_status(obj: Dict) -> None:
            """Update status in a single object"""
            if isinstance(obj, dict):
                for class_data in obj.values():
                    if isinstance(class_data, dict):
                        if "attributes" not in class_data:
                            class_data["attributes"] = {}
                        if status_value is None:
                            class_data["attributes"].pop("status", None)
                        else:
                            class_data["attributes"]["status"] = status_value

        if not config:
            return config

        if object_path:
            current = config
            for path_part in object_path:
                if isinstance(current, dict):
                    if path_part in current:
                        current = current[path_part]
                        update_status(current)
                    else:
                        break
                elif isinstance(current, list):
                    try:
                        idx = int(path_part.strip("[]"))
                        if 0 <= idx < len(current):
                            current = current[idx]
                            update_status(current)
                        else:
                            break
                    except (ValueError, IndexError):
                        break
        else:
            update_status(config)
            
            # Update children recursively
            if isinstance(config, dict):
                for value in config.values():
                    if isinstance(value, dict) and "children" in value:
                        for child in value["children"]:
                            ACIObjectExtractor.set_object_status(child, status_value)
            elif isinstance(config, list):
                for item in config:
                    ACIObjectExtractor.set_object_status(item, status_value)

        return config

    @staticmethod
    def set_status_for_child(config: Dict, child_index: int, status_value: Optional[str]) -> bool:
        """
        Set the status for a specific child by index efficiently
        
        Args:
            config: The loaded ACI configuration
            child_index: Index of the child to update (0-based)
            status_value: Status value to set or None to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            child = ACIObjectExtractor.get_child_original_config(config, 0, child_index)
            if not child:
                return False
                
            ACIObjectExtractor.set_object_status(child, status_value)
            # Clear cache since we modified the object
            ACIObjectExtractor._clear_cache()
            return True
        except Exception as e:
            print(f"Error setting status for child: {e}")
            return False