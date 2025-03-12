"""
Main APIC configuration parser module
"""
import argparse
import os
import sys
import json
from typing import Dict, List, Any, Optional, Union, Tuple

# Import from our modules
from core.extractors import ACIObjectExtractor
from core.models import ACIObject, TenantConfig
from utils.file_utils import load_json_config, save_json_config


class ACIConfigParser:
    """Main parser class for ACI configuration files"""
    
    def __init__(self, config_file: str):
        """
        Initialize the parser with a configuration file
        
        Args:
            config_file: Path to the JSON configuration file
        """
        self.config_file = config_file
        self.config = None
        self.objects = []
        self.object_hierarchy = []
        
    def load(self) -> bool:
        """
        Load and parse the configuration file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config = load_json_config(self.config_file)
            self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            self.object_hierarchy = ACIObjectExtractor.get_object_hierarchy(self.config)
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def get_object_hierarchy(self, max_depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a hierarchical representation of all objects in the configuration
        
        Args:
            max_depth: Maximum depth to traverse (default: None = unlimited)
            
        Returns:
            List of objects with their children and path information
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        return ACIObjectExtractor.get_object_hierarchy(self.config, max_depth)
    
    def get_child_config(self, parent_index: int = 0, child_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific child's configuration
        
        Args:
            parent_index: Index of the parent object (default: 0)
            child_index: Index of the child object to extract (0-based)
            
        Returns:
            Dictionary containing the child's configuration, or None if not found
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        return ACIObjectExtractor.get_child_original_config(
            self.config, parent_index, child_index
        )
    
    def get_nested_child_config(self, path: List[int]) -> Optional[Dict[str, Any]]:
        """
        Get a nested child's configuration by path
        
        Args:
            path: List of indices to navigate to the desired object
                 For example: [0, 5, 2] means "3rd child of the 6th child of the 1st parent"
            
        Returns:
            Dictionary containing the nested child configuration, or None if not found
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        return ACIObjectExtractor.get_nested_child_by_path(self.config, path)
    
    def get_multiple_children_config(self, child_indices: List[int], parent_index: int = 0) -> Dict[str, Any]:
        """
        Get multiple children's configurations and combine them into a single structure
        
        Args:
            child_indices: List of child indices to extract (0-based)
            parent_index: Index of the parent object (default: 0)
            
        Returns:
            Dictionary containing the combined configuration with multiple children
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        # Extract the root structure to replicate
        root_structure = None
        if 'imdata' in self.config and isinstance(self.config['imdata'], list) and len(self.config['imdata']) > parent_index:
            parent_obj = self.config['imdata'][parent_index]
            if parent_obj:
                parent_class = list(parent_obj.keys())[0]
                # Create a copy of the parent structure without its children
                root_structure = {
                    "totalCount": self.config.get("totalCount", "1"),
                    "imdata": [
                        {
                            parent_class: {
                                "attributes": parent_obj[parent_class].get("attributes", {}),
                                "children": []
                            }
                        }
                    ]
                }
                
        if not root_structure:
            # Create a default structure if original couldn't be extracted
            root_structure = {
                "totalCount": "1",
                "imdata": [
                    {
                        "fvTenant": {  # Default class, may need to be adjusted
                            "attributes": {},
                            "children": []
                        }
                    }
                ]
            }
            
        # Get each requested child and add it to the root structure
        children_list = []
        for idx in child_indices:
            child_config = self.get_child_config(parent_index, idx)
            if child_config:
                children_list.append(child_config)
            else:
                print(f"Warning: Child with index {idx} not found")
        
        # Add all found children to the root structure
        if children_list:
            parent_class = list(root_structure["imdata"][0].keys())[0]
            root_structure["imdata"][0][parent_class]["children"] = children_list
            
        return root_structure
    
    def get_objects_by_class(self, class_name: str) -> List[Dict[str, Any]]:
        """
        Find all objects of a specific class
        
        Args:
            class_name: The ACI class name to search for
            
        Returns:
            List of matching objects
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        return ACIObjectExtractor.extract_object(self.config, class_name)
    
    def set_object_status(self, status_value: str, object_path: Optional[List[str]] = None) -> bool:
        """
        Set the status attribute for an object in the configuration
        
        Args:
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            object_path: Path to the object to update (if None, updates root object)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            ACIObjectExtractor.set_object_status(self.config, status_value, object_path)
            # Refresh the extracted objects
            self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            return True
        except Exception as e:
            print(f"Error setting object status: {e}")
            return False
    
    def set_child_status(self, child_index: int, status_value: str) -> bool:
        """
        Set the status for a specific child by index
        
        Args:
            child_index: Index of the child to update (0-based)
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            result = ACIObjectExtractor.set_status_for_child(self.config, child_index, status_value)
            if result:
                # Refresh the extracted objects
                self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            return result
        except Exception as e:
            print(f"Error setting child status: {e}")
            return False
    
    def set_nested_child_status(self, path: List[int], status_value: Optional[str]) -> bool:
        """
        Set the status for a nested child object by path
        
        Args:
            path: List of indices to navigate to the desired object
                 For example: [0, 5, 2] means "3rd child of the 6th child of the 1st parent"
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
                         If None, status attribute will be removed
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            result = ACIObjectExtractor.set_status_for_nested_child(self.config, path, status_value)
            if result:
                # Refresh the extracted objects and hierarchy
                self.objects = ACIObjectExtractor.extract_all_objects(self.config)
                self.object_hierarchy = ACIObjectExtractor.get_object_hierarchy(self.config)
            return result
        except Exception as e:
            print(f"Error setting status for nested child: {e}")
            return False
    
    def set_multiple_children_status(self, child_indices: List[int], status_value: str) -> bool:
        """
        Set the status for multiple children by indices
        
        Args:
            child_indices: List of child indices to update (0-based)
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        success = True
        for idx in child_indices:
            try:
                result = ACIObjectExtractor.set_status_for_child(self.config, idx, status_value)
                if not result:
                    print(f"Failed to set status for child {idx}")
                    success = False
            except Exception as e:
                print(f"Error setting status for child {idx}: {e}")
                success = False
                
        # Refresh the extracted objects if any updates were successful
        if success:
            self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            
        return success
    
    def set_multiple_nested_children_status(self, paths: List[List[int]], status_value: Optional[str]) -> bool:
        """
        Set the status for multiple nested child objects by their paths
        
        Args:
            paths: List of object paths (each path is a list of indices)
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
                         If None, status attribute will be removed
            
        Returns:
            bool: True if all status updates were successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        success = True
        for path in paths:
            try:
                result = ACIObjectExtractor.set_status_for_nested_child(self.config, path, status_value)
                if not result:
                    print(f"Failed to set status for child at path {path}")
                    success = False
            except Exception as e:
                print(f"Error setting status for child at path {path}: {e}")
                success = False
                
        # Refresh the extracted objects and hierarchy if any updates were successful
        if success:
            self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            self.object_hierarchy = ACIObjectExtractor.get_object_hierarchy(self.config)
            
        return success
    
    def save_config(self, output_path: Optional[str] = None) -> bool:
        """
        Save the current configuration to a file
        
        Args:
            output_path: Path to save the configuration (if None, uses original file path)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            save_path = output_path or self.config_file
            return save_json_config(self.config, save_path)
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def print_summary(self, list_all: bool = False) -> None:
        """
        Print a summary of the configuration
        
        Args:
            list_all: Whether to list all children (default: False)
        """
        if not self.objects:
            print("No objects found. Make sure to call load() first.")
            return
            
        print(f"Found {len(self.objects)} total objects")
        
        # Print the first level objects (typically imdata and its children)
        for i, obj in enumerate(self.objects[:1]):  # Show only the first object
            print(f"- Object {i+1}: Class {obj['class']}")
            print(f"  Path: {obj['path']}")
            
            # Show some attributes if available
            if obj['attributes']:
                print(f"  Attributes: {len(obj['attributes'])} keys")
                # Print a couple of sample attributes
                for attr_name, attr_val in list(obj['attributes'].items())[:2]:
                    print(f"    {attr_name}: {attr_val}")
            
            # Show number of children
            print(f"  Children: {len(obj['children'])}")
            
            # If list_all is True, show all children
            if list_all:
                for child_idx, child in enumerate(obj['children']):
                    print(f"    - Child {child_idx+1}: Class {child['class']}")
                    if 'attributes' in child and 'name' in child['attributes']:
                        print(f"      Name: {child['attributes']['name']}")
                    if 'attributes' in child and 'descr' in child['attributes']:
                        print(f"      Description: {child['attributes']['descr']}")
                    if 'attributes' in child and 'status' in child['attributes']:
                        print(f"      Status: {child['attributes']['status']}")
            # Otherwise show just the first few
            else:
                for child_idx, child in enumerate(obj['children'][:20]):
                    print(f"    - Child {child_idx+1}: Class {child['class']}")
                    if 'attributes' in child and 'status' in child['attributes']:
                        print(f"      Status: {child['attributes']['status']}")
                    if child_idx == 19 and len(obj['children']) > 20:
                        print(f"      ... ({len(obj['children']) - 20} more)")

    def extract_child_to_file(self, child_index: int, output_path: str) -> bool:
        """
        Extract a specific child configuration and save it to a file
        
        Args:
            child_index: Index of the child to extract (0-based)
            output_path: Path where to save the extracted configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            child_config = self.get_child_config(child_index=child_index)
            if not child_config:
                print(f"Child with index {child_index} not found")
                return False
                
            return save_json_config(child_config, output_path)
        except Exception as e:
            print(f"Error extracting child configuration: {e}")
            return False
            
    def extract_nested_child_to_file(self, path: List[int], output_path: str) -> bool:
        """
        Extract a nested child configuration and save it to a file
        
        Args:
            path: List of indices to navigate to the desired object
            output_path: Path where to save the extracted configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            child_config = self.get_nested_child_config(path)
            if not child_config:
                print(f"Child at path {path} not found")
                return False
                
            return save_json_config(child_config, output_path)
        except Exception as e:
            print(f"Error extracting nested child configuration: {e}")
            return False
    
    def extract_multiple_children_to_file(self, child_indices: List[int], output_path: str) -> bool:
        """
        Extract multiple child configurations and save them as a combined file
        
        Args:
            child_indices: List of child indices to extract (0-based)
            output_path: Path where to save the extracted configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            combined_config = self.get_multiple_children_config(child_indices)
            if not combined_config or not combined_config.get('imdata', []):
                print("No valid children found to extract")
                return False
                
            return save_json_config(combined_config, output_path)
        except Exception as e:
            print(f"Error extracting multiple child configurations: {e}")
            return False
    
    def extract_multiple_nested_children_to_file(self, paths: List[List[int]], output_path: str) -> bool:
        """
        Extract multiple nested child configurations and save them as a combined file
        
        Args:
            paths: List of object paths to extract (each path is a list of indices)
            output_path: Path where to save the extracted configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract the root structure to replicate
            root_structure = None
            if 'imdata' in self.config and isinstance(self.config['imdata'], list) and len(self.config['imdata']) > 0:
                parent_obj = self.config['imdata'][0]
                if parent_obj:
                    parent_class = list(parent_obj.keys())[0]
                    # Create a copy of the parent structure without its children
                    root_structure = {
                        "totalCount": self.config.get("totalCount", "1"),
                        "imdata": [
                            {
                                parent_class: {
                                    "attributes": parent_obj[parent_class].get("attributes", {}),
                                    "children": []
                                }
                            }
                        ]
                    }
                    
            if not root_structure:
                # Create a default structure if original couldn't be extracted
                root_structure = {
                    "totalCount": "1",
                    "imdata": [
                        {
                            "fvTenant": {  # Default class, may need to be adjusted
                                "attributes": {},
                                "children": []
                            }
                        }
                    ]
                }
                
            # Get each requested child and add it to the root structure
            children_list = []
            for path in paths:
                child_config = self.get_nested_child_config(path)
                if child_config:
                    children_list.append(child_config)
                else:
                    print(f"Warning: Child at path {path} not found")
            
            # Add all found children to the root structure
            if children_list:
                parent_class = list(root_structure["imdata"][0].keys())[0]
                root_structure["imdata"][0][parent_class]["children"] = children_list
                
                return save_json_config(root_structure, output_path)
            else:
                print("No valid children found to extract")
                return False
                
        except Exception as e:
            print(f"Error extracting multiple nested child configurations: {e}")
            return False


def main():
    """Main entry point for the command line interface"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='APIC Configuration Parser')
    parser.add_argument('--file', '-f', type=str, help='Path to the configuration file', 
                       default=r"C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\APIC_Parser\tn-Datacenter1.json")
    parser.add_argument('--child', '-c', type=int, help='Index of child to extract (0-based)', default=None)
    parser.add_argument('--children', '-m', type=str, help='Comma-separated list of child indices to extract (e.g., "1,3,5")', default=None)
    parser.add_argument('--path', '-p', type=str, help='Path to nested object (e.g., "0,5,2" for 3rd child of the 6th child of 1st parent)', default=None)
    parser.add_argument('--paths', '-ps', type=str, help='Comma-separated list of paths for multiple nested objects', default=None)
    parser.add_argument('--output', '-o', type=str, help='Output file path (optional)', default=None)
    parser.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    parser.add_argument('--list', '-l', action='store_true', help='List all children')
    parser.add_argument('--hierarchy', '-h', action='store_true', help='Show object hierarchy')
    parser.add_argument('--class', '-cls', type=str, help='Search for objects of a specific class', default=None)
    parser.add_argument('--set-status', type=str, help='Set status for selected children/objects', default=None)
    parser.add_argument('--save', action='store_true', help='Save configuration after changes')
    
    args = parser.parse_args()
    
    # Check if the file exists
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found.")
        sys.exit(1)
    
    # Create parser and load configuration
    parser = ACIConfigParser(args.file)
    if not parser.load():
        sys.exit(1)
    
    # Parse multiple children indices if provided
    child_indices = []
    if args.children:
        try:
            child_indices = [int(idx.strip()) for idx in args.children.split(',')]
            print(f"Processing multiple children: {child_indices}")
        except ValueError:
            print(f"Error: Invalid format for --children parameter. Use comma-separated integers, e.g., '1,3,5'")
            sys.exit(1)
    
    # Parse path to nested object if provided
    nested_path = None
    if args.path:
        try:
            nested_path = [int(idx.strip()) for idx in args.path.split(',')]
            print(f"Processing nested object at path: {nested_path}")
        except ValueError:
            print(f"Error: Invalid format for --path parameter. Use comma-separated integers, e.g., '0,5,2'")
            sys.exit(1)
    
    # Parse multiple paths for nested objects if provided
    nested_paths = []
    if args.paths:
        try:
            path_strings = args.paths.split(';')
            for path_str in path_strings:
                path = [int(idx.strip()) for idx in path_str.split(',')]
                nested_paths.append(path)
            print(f"Processing multiple nested objects at paths: {nested_paths}")
        except ValueError:
            print(f"Error: Invalid format for --paths parameter. Use semicolon-separated lists of comma-separated indices, e.g., '0,1,2;0,3,4'")
            sys.exit(1)
    
    # Show hierarchy if requested
    if args.hierarchy:
        print("\n--- Object Hierarchy ---")
        hierarchy = parser.get_object_hierarchy()
        
        for item in hierarchy:
            print(f"Root: {item['class']} - {item['name']}")
            
            def print_children(children, level=1):
                for child in children:
                    indent = "  " * level
                    status = f" | Status: {child['status']}" if child.get('status', 'None') != 'None' else ""
                    print(f"{indent}- {child['class']} - {child['name']} | Path: {child['path']}{status}")
                    
                    if child.get('children'):
                        print_children(child['children'], level + 1)
            
            print_children(item['children'])
    
    # Handle status setting if requested
    if args.set_status:
        # Determine target object(s) based on provided options
        if args.child is not None:
            print(f"Setting status for child {args.child} to '{args.set_status}'")
            if parser.set_child_status(args.child, args.set_status):
                print(f"Status successfully set to '{args.set_status}'")
                # Save if requested
                if args.save:
                    save_path = args.output or args.file
                    if parser.save_config(save_path):
                        print(f"Configuration saved to {save_path}")
                    else:
                        print("Failed to save configuration")
            else:
                print(f"Failed to set status for child {args.child}")
                sys.exit(1)
                
        elif nested_path:
            print(f"Setting status for nested object at path {nested_path} to '{args.set_status}'")
            status_value = None if args.set_status.lower() == "none" else args.set_status
            if parser.set_nested_child_status(nested_path, status_value):
                print(f"Status successfully set to '{status_value}'")
                # Save if requested
                if args.save:
                    save_path = args.output or args.file
                    if parser.save_config(save_path):
                        print(f"Configuration saved to {save_path}")
                    else:
                        print("Failed to save configuration")
            else:
                print(f"Failed to set status for nested object at path {nested_path}")
                sys.exit(1)
                
        elif child_indices:
            print(f"Setting status for children {child_indices} to '{args.set_status}'")
            if parser.set_multiple_children_status(child_indices, args.set_status):
                print(f"Status successfully set to '{args.set_status}' for all specified children")
                # Save if requested
                if args.save:
                    save_path = args.output or args.file
                    if parser.save_config(save_path):
                        print(f"Configuration saved to {save_path}")
                    else:
                        print("Failed to save configuration")
            else:
                print(f"Failed to set status for some or all children")
                sys.exit(1)
                
        elif nested_paths:
            print(f"Setting status for nested objects at paths {nested_paths} to '{args.set_status}'")
            status_value = None if args.set_status.lower() == "none" else args.set_status
            if parser.set_multiple_nested_children_status(nested_paths, status_value):
                print(f"Status successfully set to '{status_value}' for all specified nested objects")
                # Save if requested
                if args.save:
                    save_path = args.output or args.file
                    if parser.save_config(save_path):
                        print(f"Configuration saved to {save_path}")
                    else:
                        print("Failed to save configuration")
            else:
                print(f"Failed to set status for some or all nested objects")
                sys.exit(1)
                
        else:
            print("Error: --set-status requires specifying target objects using --child, --children, --path, or --paths")
            sys.exit(1)
    
    # Process based on the arguments (extraction requests)
    if args.child is not None:
        print(f"\n--- Getting Child {args.child}'s original configuration ---")
        child_config = parser.get_child_config(child_index=args.child)
        
        if child_config:
            # Get the class name
            child_class = list(child_config.keys())[0]
            print(f"Child {args.child} class: {child_class}")
            
            # Get the name if available
            if 'attributes' in child_config[child_class] and 'name' in child_config[child_class]['attributes']:
                print(f"Name: {child_config[child_class]['attributes']['name']}")
            
            # Get the description if available
            if 'attributes' in child_config[child_class] and 'descr' in child_config[child_class]['attributes']:
                print(f"Description: {child_config[child_class]['attributes']['descr']}")
            
            # Get the status if available
            if 'attributes' in child_config[child_class] and 'status' in child_config[child_class]['attributes']:
                print(f"Status: {child_config[child_class]['attributes']['status']}")
            
            # Output the configuration
            if args.output and not args.save:  # Skip if we've already saved with --save
                if parser.extract_child_to_file(args.child, args.output):
                    print(f"\nConfiguration saved to {args.output}")
            else:
                # Print to console
                print("\nOriginal configuration:")
                print(json.dumps(child_config, indent=2))
    
    elif nested_path:
        print(f"\n--- Getting nested object at path {nested_path} ---")
        nested_config = parser.get_nested_child_config(nested_path)
        
        if nested_config:
            # Get the class name
            nested_class = list(nested_config.keys())[0]
            print(f"Object class: {nested_class}")
            
            # Get the name if available
            if 'attributes' in nested_config[nested_class] and 'name' in nested_config[nested_class]['attributes']:
                print(f"Name: {nested_config[nested_class]['attributes']['name']}")
            
            # Get the description if available
            if 'attributes' in nested_config[nested_class] and 'descr' in nested_config[nested_class]['attributes']:
                print(f"Description: {nested_config[nested_class]['attributes']['descr']}")
            
            # Get the status if available
            if 'attributes' in nested_config[nested_class] and 'status' in nested_config[nested_class]['attributes']:
                print(f"Status: {nested_config[nested_class]['attributes']['status']}")
            
            # Output the configuration
            if args.output and not args.save:  # Skip if we've already saved with --save
                if parser.extract_nested_child_to_file(nested_path, args.output):
                    print(f"\nConfiguration saved to {args.output}")
            else:
                # Print to console
                print("\nOriginal configuration:")
                print(json.dumps(nested_config, indent=2))
    
    elif child_indices:
        print(f"\n--- Getting configuration for children {child_indices} ---")
        # Extract and save multiple children to file if output path is specified
        if args.output and not args.save:  # Skip if we've already saved with --save
            if parser.extract_multiple_children_to_file(child_indices, args.output):
                print(f"\nCombined configuration saved to {args.output}")
            else:
                print(f"Failed to save combined configuration")
        else:
            # Just show summary information about the selected children
            for idx in child_indices:
                child_config = parser.get_child_config(child_index=idx)
                if child_config:
                    child_class = list(child_config.keys())[0]
                    print(f"\nChild {idx} class: {child_class}")
                    if 'attributes' in child_config[child_class] and 'name' in child_config[child_class]['attributes']:
                        print(f"Name: {child_config[child_class]['attributes']['name']}")
                    if 'attributes' in child_config[child_class] and 'descr' in child_config[child_class]['attributes']:
                        print(f"Description: {child_config[child_class]['attributes']['descr']}")
                else:
                    print(f"\nChild {idx} not found")
    
    elif nested_paths:
        print(f"\n--- Getting configuration for nested objects at paths {nested_paths} ---")
        # Extract and save multiple nested objects to file if output path is specified
        if args.output and not args.save:  # Skip if we've already saved with --save
            if parser.extract_multiple_nested_children_to_file(nested_paths, args.output):
                print(f"\nCombined configuration saved to {args.output}")
            else:
                print(f"Failed to save combined configuration")
        else:
            # Just show summary information about the selected nested objects
            for path in nested_paths:
                nested_config = parser.get_nested_child_config(path)
                if nested_config:
                    nested_class = list(nested_config.keys())[0]
                    print(f"\nObject at path {path} class: {nested_class}")
                    if 'attributes' in nested_config[nested_class] and 'name' in nested_config[nested_class]['attributes']:
                        print(f"Name: {nested_config[nested_class]['attributes']['name']}")
                    if 'attributes' in nested_config[nested_class] and 'descr' in nested_config[nested_class]['attributes']:
                        print(f"Description: {nested_config[nested_class]['attributes']['descr']}")
                else:
                    print(f"\nObject at path {path} not found")
    
    elif getattr(args, 'class'):
        class_name = getattr(args, 'class')
        print(f"Searching for objects of class {class_name}...")
        objects = parser.get_objects_by_class(class_name)
        print(f"Found {len(objects)} objects of class {class_name}")
        
        # Display the first few
        for i, obj in enumerate(objects[:5]):
            print(f"\nObject {i+1}:")
            print(json.dumps(obj, indent=2))
            if i == 4 and len(objects) > 5:
                print(f"\n...and {len(objects) - 5} more")
    
    else:
        # Show summary
        parser.print_summary(list_all=args.list)
        
        # If no specific action requested, show usage hint
        if not args.summary and not args.list and not args.hierarchy and args.set_status is None:
            print("\nTo see all objects, use --list or -l flag")
            print("To view object hierarchy, use --hierarchy or -h flag")
            print("To extract a specific child, use --child <index> or -c <index>")
            print("To extract multiple children, use --children '1,3,5' or -m '1,3,5'")
            print("To extract a nested object, use --path '0,5,2' or -p '0,5,2'")
            print("To extract multiple nested objects, use --paths '0,1,2;0,3,4' or -ps '0,1,2;0,3,4'")
            print("To search for objects by class, use --class <class_name> or -cls <class_name>")
            print("To set status for a child, use --child <index> --set-status <status>")
            print("To set status for a nested object, use --path '0,5,2' --set-status <status>")
            print("To set status for multiple children, use --children '1,3,5' --set-status <status>")
            print("To set status for multiple nested objects, use --paths '0,1,2;0,3,4' --set-status <status>")
            print("  Valid status values: 'created', 'modified, created', 'deleted', 'None'")
            print("To save changes, add --save flag")


if __name__ == "__main__":
    main()
