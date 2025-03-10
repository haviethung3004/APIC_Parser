"""
Main APIC configuration parser module
"""
import argparse
import os
import sys
import json
from typing import Dict, Any, Optional, List

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


def main():
    """Main entry point for the command line interface"""
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='APIC Configuration Parser')
    parser.add_argument('--file', '-f', type=str, help='Path to the configuration file', 
                       default=r"C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\APIC_Parser\tn-Datacenter1.json")
    parser.add_argument('--child', '-c', type=int, help='Index of child to extract (0-based)', default=None)
    parser.add_argument('--output', '-o', type=str, help='Output file path (optional)', default=None)
    parser.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    parser.add_argument('--list', '-l', action='store_true', help='List all children')
    parser.add_argument('--class', '-cls', type=str, help='Search for objects of a specific class', default=None)
    parser.add_argument('--set-status', type=str, help='Set status for a child (requires --child)', default=None)
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
    
    # Handle status setting if requested
    if args.set_status:
        if args.child is None:
            print("Error: --set-status requires --child option to specify which child to update")
            sys.exit(1)
        
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
    
    # Process based on the arguments
    if args.child is not None:
        print(f"\n--- Getting Child {args.child+1}'s original configuration ---")
        child_config = parser.get_child_config(child_index=args.child)
        
        if child_config:
            # Get the class name
            child_class = list(child_config.keys())[0]
            print(f"Child {args.child+1} class: {child_class}")
            
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
            print("To search for objects by class, use --class <class_name> or -cls <class_name>")
            print("To set status for a child, use --child <index> --set-status <status>")
            print("  Valid status values: 'created', 'modified, created', 'deleted'")
            print("To save changes, add --save flag")


if __name__ == "__main__":
    main()
