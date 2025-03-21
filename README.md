# APIC Parser

A Python tool for parsing and extracting objects from Cisco ACI (Application Centric Infrastructure) configuration files.

## Overview

APIC Parser is designed to help network administrators and automation engineers extract and manipulate Cisco ACI configuration objects from JSON exports. It provides functionality to:

- Parse and analyze ACI configuration files
- Extract specific child objects by index
- Extract multiple child objects simultaneously
- Manage nested children objects within parent objects
- Search for objects by class name
- Generate summaries of configuration hierarchies
- Export configurations to separate files
- Set status attributes for objects (created, modified, deleted)

## Installation

No installation is required. Simply clone or download the repository and ensure you have Python 3.6+ installed.

```bash
git clone <repository-url>
cd APIC_Parser
```

For the web interface, you'll need to install Streamlit:

```bash
pip install streamlit pandas
```

## Usage

### Command Line Interface

```bash
python apic_parser.py [OPTIONS]
```

### Web Interface

```bash
streamlit run apic_app.py
```

This will start a local web server and open the APIC Parser web interface in your browser.

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file FILE` | `-f FILE` | Path to the configuration file |
| `--child INDEX` | `-c INDEX` | Index of child to extract (0-based) |
| `--children LIST` | `-m LIST` | Comma-separated list of child indices to extract (e.g., "1,3,5") |
| `--output FILE` | `-o FILE` | Output file path for extracted configuration |
| `--summary` | `-s` | Show summary only |
| `--list` | `-l` | List all children |
| `--class CLASS` | `-cls CLASS` | Search for objects of a specific class |
| `--set-status STATUS` | | Set status for selected children |
| `--save` | | Save configuration after changes |
| `--help` | `-h` | Show help message |

### Examples

1. Show a summary of the configuration:

```bash
python apic_parser.py -f your_config.json
```

2. List all children in the configuration:

```bash
python apic_parser.py -f your_config.json --list
```

3. Extract a specific child object:

```bash
python apic_parser.py -f your_config.json -c 9
```

4. Extract multiple child objects:

```bash
python apic_parser.py -f your_config.json -m "9,12,15"
```

5. Save a child object to a separate file:

```bash
python apic_parser.py -f your_config.json -c 9 -o child9.json
```

6. Save multiple child objects to a single file:

```bash
python apic_parser.py -f your_config.json -m "9,12,15" -o multi_children.json
```

7. Search for objects of a specific class:

```bash
python apic_parser.py -f your_config.json --class fvBD
```

8. Set status attribute for a child object:

```bash
python apic_parser.py -f your_config.json -c 3 --set-status "created" --save
```

9. Set status attribute for multiple child objects:

```bash
python apic_parser.py -f your_config.json -m "3,5,7" --set-status "created" --save
```

10. Mark a child object as deleted:

```bash
python apic_parser.py -f your_config.json -c 5 --set-status "deleted" --save
```

11. Mark multiple child objects as modified:

```bash
python apic_parser.py -f your_config.json -m "2,4,6" --set-status "modified, created" --save
```

## Web Interface Features

The Streamlit-based web interface provides a user-friendly way to interact with ACI configuration files through several tabs:

### Summary Tab
- Visual summaries of your configuration with charts
- Object class distribution overview
- Root object details with expandable sections

### Objects & Extraction Tab
- Filter objects by class and status
- View details of any selected object
- Extract individual or multiple objects with a single click

#### Object Details Subtab
- View detailed information about selected objects 
- Inspect attributes and children of objects
- View raw JSON configuration

#### Extract & Modify Subtab
- Single object or multi-object selection modes
- Preview configurations before extraction
- Set status attributes (create, modify, delete)
- Export configurations to downloadable JSON files
- Save changes back to the original configuration

#### Class Operations Subtab
- Filter and work with objects of a specific class
- Perform bulk operations on objects of the same class
- Set status attributes for multiple objects simultaneously

#### Children Manager Subtab
- Manage nested children of parent objects (like fvAP objects)
- View the hierarchical structure of complex objects
- Sort parent objects by number of children
- Select and modify individual or multiple nested children
- Extract nested children with updated status values
- Apply status changes to multiple nested children at once

## Object Selection Features

### Multiple Object Selection
The multiple object selection feature allows you to work with several objects simultaneously:

- Extract multiple objects from a configuration into a single combined JSON file
- Set the same status for multiple objects at once (created, modified, deleted)
- Maintain the hierarchical structure of the original configuration
- Preserve the parent object's attributes while including only the selected child objects

### Children Management
The children management feature allows you to:

- Visualize and navigate the nested hierarchy of complex ACI objects
- Perform operations on deeply nested children (3+ levels deep)
- Extract specific children from parent objects that might have hundreds of children
- Apply status changes to children objects while maintaining their relationships
- Export selected children configurations for later use

## Status Attribute Feature

The status attribute feature allows you to add or modify the `status` field in an object's attributes. This can be useful for:

- Tracking changes to objects in your ACI configuration
- Marking objects for creation, modification or deletion in automation workflows
- Implementing change management processes

Valid status values include:
- `created`: New objects that need to be created
- `modified, created`: Objects that exist but need modifications
- `deleted`: Objects that should be removed

## Project Structure

```
APIC_Parser/
├── apic_parser.py       # Main entry point script for CLI
├── apic_app.py          # Streamlit web application
├── README.md            # This file
├── core/                # Core functionality
│   ├── __init__.py
│   ├── extractors.py    # Object extraction logic
│   ├── models.py        # Data models for ACI objects
│   └── parser.py        # Main parser implementation
└── utils/               # Utility modules
    └── file_utils.py    # File handling utilities
```

## Core Components

- **ACIConfigParser**: Main class for parsing and analyzing configuration files
- **ACIObjectExtractor**: Handles the extraction of objects from the configuration hierarchy
- **ACIObject**: Data model representing an ACI object with its attributes and children
- **TenantConfig**: Represents a full tenant configuration with its child objects

## Performance Optimizations

The application includes several optimizations to handle large configuration files efficiently:

- Lazy loading of large object trees
- Efficient filtering of object collections
- Smart status propagation through object hierarchies
- Optimized JSON handling for large configurations
- Selective extraction of nested objects without loading entire trees

## Development

### Dependencies

- Python 3.6+
- Standard library only (no external dependencies) for CLI
- Streamlit and pandas for web interface

### Extending the Parser

To add new functionality:

1. Add new methods to the `ACIConfigParser` class in `core/parser.py`
2. Update the command-line interface in the `main()` function
3. Add any new utility functions to the appropriate modules
4. Update the web interface in `apic_app.py` to expose new features

## License

[Specify your license here]
