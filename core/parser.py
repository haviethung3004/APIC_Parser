"""
Main APIC configuration parser module
"""
import argparse
import os
import sys
import json
from typing import Dict, Any, Optional, List, Tuple

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
        
    def load(self) -> bool:
        """
        Load and parse the configuration file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config = load_json_config(self.config_file)
            self.objects = ACIObjectExtractor.extract_all_objects(self.config)
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
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
    
    def get_child_indices_by_class(self, class_name: str) -> List[int]:
        """
        Get indices of all children of a specific class
        
        Args:
            class_name: The class name to find (e.g., "fvAP")
            
        Returns:
            List of indices for children matching the specified class
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        indices = []
        
        # Check if we have the root object with children
        if 'imdata' in self.config and isinstance(self.config['imdata'], list) and len(self.config['imdata']) > 0:
            parent_obj = self.config['imdata'][0]
            if parent_obj:
                parent_class = list(parent_obj.keys())[0]
                if 'children' in parent_obj[parent_class]:
                    # Iterate through children to find those matching the class
                    for i, child in enumerate(parent_obj[parent_class]['children']):
                        if child and len(child) == 1:  # Each child should have one key (class)
                            child_class = list(child.keys())[0]
                            if child_class == class_name:
                                indices.append(i)
        
        return indices
        
    def get_class_children_config(self, class_name: str) -> Dict[str, Any]:
        """
        Get configuration for all children of a specific class
        
        Args:
            class_name: The class name to collect (e.g., "fvAP")
            
        Returns:
            Dictionary containing the combined configuration with all children of the specified class
        """
        # Get indices of all children matching the class
        indices = self.get_child_indices_by_class(class_name)
        
        # Use existing function to get the combined config
        return self.get_multiple_children_config(indices)
    
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
    
    def set_class_children_status(self, class_name: str, status_value: str) -> bool:
        """
        Set the status for all children of a specific class
        
        Args:
            class_name: The class name to target (e.g., "fvAP")
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            bool: True if successful, False otherwise, and count of updated objects
        """
        # Get indices of all children matching the class
        indices = self.get_child_indices_by_class(class_name)
        
        # Use existing function to update all children
        success = self.set_multiple_children_status(indices, status_value)
        
        return success, len(indices)
    
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
    
    def get_class_counts(self) -> Dict[str, int]:
        """
        Get counts of each class in the configuration
        
        Returns:
            Dictionary with class names as keys and counts as values
        """
        if not self.objects:
            return {}
            
        class_counts = {}
        
        # Count root level objects
        for obj in self.objects:
            class_name = obj['class']
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            # Count children
            for child in obj['children']:
                child_class = child['class']
                class_counts[child_class] = class_counts.get(child_class, 0) + 1
                
                # Count grandchildren and deeper (recursive)
                def count_children_classes(obj_list):
                    for child_obj in obj_list:
                        if isinstance(child_obj, dict) and 'class' in child_obj:
                            class_name = child_obj['class']
                            class_counts[class_name] = class_counts.get(class_name, 0) + 1
                            # Process children recursively
                            if 'children' in child_obj and child_obj['children']:
                                count_children_classes(child_obj['children'])
                
                if 'children' in child and child['children']:
                    count_children_classes(child['children'])
                
        return class_counts
        
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
    
    def extract_class_children_to_file(self, class_name: str, output_path: str) -> bool:
        """
        Extract all children of a specific class and save them as a combined file
        
        Args:
            class_name: The class name to extract (e.g., "fvAP") 
            output_path: Path where to save the extracted configuration
            
        Returns:
            bool: True if successful, False otherwise, and count of extracted objects
        """
        try:
            # Get indices of all children matching the class
            indices = self.get_child_indices_by_class(class_name)
            
            if not indices:
                print(f"No children found with class '{class_name}'")
                return False, 0
                
            # Use existing function to extract all children
            success = self.extract_multiple_children_to_file(indices, output_path)
            
            return success, len(indices)
        except Exception as e:
            print(f"Error extracting children of class {class_name}: {e}")
            return False, 0

    def get_child_children(self, child_index: int) -> List[Dict[str, Any]]:
        """
        Get children objects of a specific child by index
        
        Args:
            child_index: Index of the parent child to get children from
            
        Returns:
            List of children objects with their attributes
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            # Get the child configuration
            child_config = self.get_child_config(child_index=child_index)
            if not child_config:
                return []
                
            # Extract the children
            child_class = list(child_config.keys())[0]
            if 'children' in child_config[child_class]:
                return child_config[child_class]['children']
            else:
                return []
        except Exception as e:
            print(f"Error getting child's children: {e}")
            return []
    
    def set_child_child_status(self, child_index: int, child_child_index: int, status_value: str) -> bool:
        """
        Set status for a specific child's child by index
        
        Args:
            child_index: Index of the parent child
            child_child_index: Index of the child's child to update 
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            # Navigate to the main object and its child
            if 'imdata' in self.config and isinstance(self.config['imdata'], list):
                parent_obj = self.config['imdata'][0]  # Typically the first object is the parent
                parent_class = list(parent_obj.keys())[0]
                
                if 'children' in parent_obj[parent_class]:
                    children = parent_obj[parent_class]['children']
                    
                    if 0 <= child_index < len(children):
                        child = children[child_index]
                        child_class = list(child.keys())[0]
                        
                        if 'children' in child[child_class]:
                            child_children = child[child_class]['children']
                            
                            if 0 <= child_child_index < len(child_children):
                                # Found the child's child, update its status
                                child_child = child_children[child_child_index]
                                child_child_class = list(child_child.keys())[0]
                                
                                if 'attributes' not in child_child[child_child_class]:
                                    child_child[child_child_class]['attributes'] = {}
                                    
                                if status_value is None:
                                    # Remove status if set to None
                                    if 'status' in child_child[child_child_class]['attributes']:
                                        del child_child[child_child_class]['attributes']['status']
                                else:
                                    # Set the status
                                    child_child[child_child_class]['attributes']['status'] = status_value
                                    
                                # Update the objects
                                self.objects = ACIObjectExtractor.extract_all_objects(self.config)
                                return True
            
            return False
        except Exception as e:
            print(f"Error setting child's child status: {e}")
            return False
    
    def set_multiple_child_children_status(self, child_index: int, child_child_indices: List[int], status_value: str) -> bool:
        """
        Set status for multiple child's children by indices
        
        Args:
            child_index: Index of the parent child
            child_child_indices: List of indices for the child's children to update
            status_value: Status value to set (e.g., "created", "modified, created", "deleted")
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        success = True
        for idx in child_child_indices:
            result = self.set_child_child_status(child_index, idx, status_value)
            if not result:
                success = False
                
        return success
    
    def get_child_child_config(self, child_index: int, child_child_index: int) -> Dict[str, Any]:
        """
        Get the configuration for a specific child's child
        
        Args:
            child_index: Index of the parent child
            child_child_index: Index of the child's child
            
        Returns:
            Dictionary with the child's child configuration, or empty dict if not found
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            child_children = self.get_child_children(child_index)
            if child_children and 0 <= child_child_index < len(child_children):
                return child_children[child_child_index]
            return {}
        except Exception as e:
            print(f"Error getting child's child configuration: {e}")
            return {}
    
    def get_multiple_child_children_config(self, child_index: int, child_child_indices: List[int]) -> Dict[str, Any]:
        """
        Get configurations for multiple children of a specific child
        
        Args:
            child_index: Index of the parent child
            child_child_indices: List of indices for the child's children
            
        Returns:
            Dictionary containing the combined configuration with all selected children
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
            
        try:
            # Get the child configuration to use as a template
            child_config = self.get_child_config(child_index=child_index)
            if not child_config:
                return {}
                
            # Create a copy of the child config without its children
            child_class = list(child_config.keys())[0]
            result = {
                child_class: {
                    "attributes": child_config[child_class].get("attributes", {}),
                    "children": []
                }
            }
            
            # Get each requested child's child and add it to the result
            child_children = self.get_child_children(child_index)
            for idx in child_child_indices:
                if 0 <= idx < len(child_children):
                    result[child_class]["children"].append(child_children[idx])
            
            return result
        except Exception as e:
            print(f"Error getting multiple child children configurations: {e}")
            return {}
    
    def extract_child_children_to_file(self, child_index: int, child_child_indices: List[int], output_path: str) -> Tuple[bool, int]:
        """
        Extract multiple children of a child and save them to a file
        
        Args:
            child_index: Index of the parent child
            child_child_indices: List of indices of the child's children to extract
            output_path: Path where to save the extracted configuration
            
        Returns:
            Tuple of (success, count of extracted objects)
        """
        try:
            config = self.get_multiple_child_children_config(child_index, child_child_indices)
            if not config:
                return False, 0
                
            # Save the configuration to file
            if save_json_config(config, output_path):
                return True, len(child_child_indices)
            else:
                return False, 0
        except Exception as e:
            print(f"Error extracting child's children: {e}")
            return False, 0


def main():
    """Main entry point for the command line interface"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='APIC Configuration Parser')
    parser.add_argument('--file', '-f', type=str, help='Path to the configuration file', 
                       default=r"C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\APIC_Parser\tn-Datacenter1.json")
    parser.add_argument('--child', '-c', type=int, help='Index of child to extract (0-based)', default=None)
    parser.add_argument('--children', '-m', type=str, help='Comma-separated list of child indices to extract (e.g., "1,3,5")', default=None)
    parser.add_argument('--output', '-o', type=str, help='Output file path (optional)', default=None)
    parser.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    parser.add_argument('--list', '-l', action='store_true', help='List all children')
    parser.add_argument('--class', '-cls', type=str, help='Search for objects of a specific class', default=None)
    parser.add_argument('--set-status', type=str, help='Set status for selected children', default=None)
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
    
    # Handle status setting if requested
    if args.set_status:
        # Determine whether to update a single child or multiple children
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
        else:
            print("Error: --set-status requires either --child or --children option to specify which children to update")
            sys.exit(1)
    
    # Process based on the arguments
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
        if not args.summary and not args.list and args.set_status is None:
            print("\nTo see all objects, use --list or -l flag")
            print("To extract a specific child, use --child <index> or -c <index>")
            print("To extract multiple children, use --children '1,3,5' or -m '1,3,5'")
            print("To search for objects by class, use --class <class_name> or -cls <class_name>")
            print("To set status for a child, use --child <index> --set-status <status>")
            print("To set status for multiple children, use --children '1,3,5' --set-status <status>")
            print("  Valid status values: 'created', 'modified, created', 'deleted'")
            print("To save changes, add --save flag")


if __name__ == "__main__":
    main()
