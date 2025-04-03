import json
from apic_parser.apic_parser import build_nested_object, get_top_level_objects, find_object_by_name_iterative, find_all_objects_by_name_iterative, save_to_json, format_result_in_apic_standard
import argparse

def main(args):
    # Build the nested object
    parser = build_nested_object(args.json_file_path)

    # Get the top-level objects if requested
    if args.get_top_level:
        top_level_objects = get_top_level_objects(parser)
        print("Top Level Objects:")
        for obj in top_level_objects:
            for key, value in obj.items():
                if key != "children":
                    print(f"Object Type: {key}, Name: {value}")
    
    # Find object by name if requested
    if args.find_object:
        if not args.object_type or not args.object_name:
            print("Error: To find an object, you must provide both --object-type and --object-name")
        else:
            # Check if multiple object names are provided (comma-separated)
            object_names = [name.strip() for name in args.object_name.split(',')]
            
            if len(object_names) > 1:
                # Multiple object names provided - use find_all_objects_by_name_iterative
                print(f"Searching for objects of type '{args.object_type}' with names: {', '.join(object_names)}")
                results = find_all_objects_by_name_iterative(parser, args.object_type, object_names)
                
                # Format the results in APIC standard format
                formatted_results = format_result_in_apic_standard(results)
                
                if results:
                    print(f"Found {len(results)} object(s) of type '{args.object_type}'")
                    if args.output_file:
                        save_to_json(args.output_file, formatted_results)
                        print(f"Objects saved to {args.output_file}")
                    else:
                        print(json.dumps(formatted_results, indent=2))
                else:
                    print(f"No objects of type '{args.object_type}' with the specified names were found.")
            else:
                # Single object name - use find_object_by_name_iterative for backward compatibility
                object_name = object_names[0]
                result = find_object_by_name_iterative(parser, args.object_type, object_name)
                
                # Format the result in APIC standard format
                formatted_result = format_result_in_apic_standard(result)
                
                if result:
                    print(f"Found object of type '{args.object_type}' with name '{object_name}':")
                    if args.output_file:
                        save_to_json(args.output_file, formatted_result)
                        print(f"Object saved to {args.output_file}")
                    else:
                        print(json.dumps(formatted_result, indent=2))
                else:
                    print(f"No object of type '{args.object_type}' with name '{object_name}' found.")
    
    # If no specific action requested, show a message
    if not (args.get_top_level or args.find_object):
        print("Nested object built successfully. Use --top-level to view top-level objects or --find-object to search for a specific object.")
    
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Parse APIC JSON configuration files.')
    parser.add_argument('-f', '--file', 
                        dest='json_file_path',
                        default=r'C:\Users\dsu979\Documents\APIC\APIC_Parser\tn-Datacenter1.json',
                        help='Path to the APIC JSON file to parse')
    parser.add_argument('-t', '--top-level',
                        dest='get_top_level',
                        action='store_true',
                        help='Get and display top-level objects from the APIC JSON file')
    parser.add_argument('--find-object',
                        action='store_true',
                        help='Find an object by type and name')
    parser.add_argument('--object-type',
                        help='Type of object to find (e.g., "fvBD")')
    parser.add_argument('--object-name',
                        help='Name of object to find (e.g., "BD_484") or a comma-separated list of names (e.g., "BD_484,BD_721")')
    parser.add_argument('--output-file',
                        help='Save the found object to this file path')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run main function with the parsed arguments
    main(args)
