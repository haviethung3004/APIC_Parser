#!/usr/bin/env python3
"""
APIC Parser - A tool for parsing and searching APIC JSON configuration files.

This module provides the main entry point for the APIC Parser tool, which allows
users to parse Cisco ACI APIC JSON configuration files and search for specific objects.
"""

import json
import argparse
import sys
from apic_parser.apic_parser import (
    build_nested_object, 
    get_top_level_objects, 
    find_object_by_name_iterative,
    find_all_objects_by_name_iterative, 
    save_to_json, 
    format_result_in_apic_standard,
    set_object_status
)


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Parse and search Cisco ACI APIC JSON configuration files.'
    )
    parser.add_argument(
        '-f', '--file', 
        dest='json_file_path',
        default=r'C:\Users\dsu979\Documents\APIC\APIC_Parser\tn-Datacenter1.json',
        help='Path to the APIC JSON file to parse'
    )
    parser.add_argument(
        '-t', '--top-level',
        dest='get_top_level',
        action='store_true',
        help='Display top-level objects from the APIC JSON file'
    )
    parser.add_argument(
        '--find-object',
        action='store_true',
        help='Find object(s) by type and name'
    )
    parser.add_argument(
        '--object-type',
        help='Type of object to find (e.g., "fvBD")'
    )
    parser.add_argument(
        '--object-name',
        help='Name of object to find (e.g., "BD_484") or a comma-separated list (e.g., "BD_484,BD_721")'
    )
    parser.add_argument(
        '--output-file',
        help='Save the found object(s) to this file path'
    )
    parser.add_argument(
        '--set-status',
        choices=['create', 'delete'],
        help='Set status for the found objects (create: "created,modified", delete: "deleted")'
    )
    
    return parser.parse_args()


def display_top_level_objects(data):
    """
    Display the top-level objects found in the APIC data.
    
    Args:
        data (dict): The parsed APIC data
    """
    top_level_objects = get_top_level_objects(data)
    print("Top Level Objects:")
    for obj in top_level_objects:
        for key, value in obj.items():
            if key != "children":
                print(f"Object Type: {key}, Name: {value}")


def find_objects(data, object_type, object_name_input, output_file=None, status=None):
    """
    Find objects by type and name(s) in the parsed APIC data.
    
    Args:
        data (dict): The parsed APIC data
        object_type (str): Type of object to find (e.g., "fvBD")
        object_name_input (str): Name or comma-separated names to find
        output_file (str, optional): Path to save the results
        status (str, optional): Status to set - either 'create' or 'delete'
    
    Returns:
        bool: True if objects were found, False otherwise
    """
    # Parse object names (handle comma-separated values)
    object_names = [name.strip() for name in object_name_input.split(',')]
    
    if len(object_names) > 1:
        # Multiple object names - use find_all_objects_by_name_iterative
        results = find_all_objects_by_name_iterative(data, object_type, object_names)
        formatted_results = format_result_in_apic_standard(results)
        
        if results:
            print(f"Found {len(results)} object(s) of type '{object_type}'")
            
            # Set status if requested
            if status:
                formatted_results = set_object_status(formatted_results, object_names, status)
                print(f"Status set to '{status}' for specified objects")
            
            if output_file:
                save_to_json(output_file, formatted_results)
                print(f"Objects saved to {output_file}")
            else:
                print(json.dumps(formatted_results, indent=2))
            return True
        else:
            print(f"No objects of type '{object_type}' with the specified names were found.")
            return False
    else:
        # Single object name - use find_object_by_name_iterative
        object_name = object_names[0]
        result = find_object_by_name_iterative(data, object_type, object_name)
        formatted_result = format_result_in_apic_standard(result)
        
        if result:
            print(f"Found object of type '{object_type}' with name '{object_name}'")
            
            # Set status if requested
            if status:
                formatted_result = set_object_status(formatted_result, [object_name], status)
                print(f"Status set to '{status}' for {object_name}")
            
            if output_file:
                save_to_json(output_file, formatted_result)
                print(f"Object saved to {output_file}")
            else:
                print(json.dumps(formatted_result, indent=2))
            return True
        else:
            return False


def main():
    """Main entry point for the APIC Parser tool."""
    args = parse_arguments()
    
    # Parse the JSON file
    try:
        parser = build_nested_object(args.json_file_path)
    except FileNotFoundError:
        print(f"Error: Could not find file '{args.json_file_path}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{args.json_file_path}' is not a valid JSON file")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)
    
    # Process command line arguments
    action_performed = False
    
    # Get top-level objects if requested
    if args.get_top_level:
        display_top_level_objects(parser)
        action_performed = True
    
    # Find object by name if requested
    if args.find_object:
        if not args.object_type or not args.object_name:
            print("Error: To find an object, you must provide both --object-type and --object-name")
        else:
            find_objects(parser, args.object_type, args.object_name, args.output_file, args.set_status)
            action_performed = True
    
    # If no specific action was requested, show usage help
    if not action_performed:
        print("Nested object built successfully. Use one of the following options:")
        print("  --top-level                To view top-level objects")
        print("  --find-object              To search for specific objects")
        print("Run with --help for full usage information.")
    

if __name__ == "__main__":
    main()
