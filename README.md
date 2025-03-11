# APIC Parser

A Python tool for parsing and extracting objects from Cisco ACI (Application Centric Infrastructure) configuration files.

## Overview

APIC Parser is designed to help network administrators and automation engineers extract and manipulate Cisco ACI configuration objects from JSON exports. It provides functionality to:

- Parse and analyze ACI configuration files
- Extract specific child objects by index
- Extract multiple child objects simultaneously
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

The Streamlit-based web interface provides a user-friendly way to interact with ACI configuration files:

- **File Upload**: Upload your ACI configuration JSON files
- **Sample Files**: Load included sample configurations
- **Summary View**: Visual summary of the configuration with charts
- **Child Objects**: View and manage all child objects
- **Extract Child**: Extract and download specific child objects
- **Class Search**: Search for objects by class name
- **Status Management**: Set status attributes for objects easily and save changes

## Multiple Object Selection Feature

The multiple object selection feature allows you to work with several objects simultaneously:

- Extract multiple objects from a configuration into a single combined JSON file
- Set the same status for multiple objects at once (created, modified, deleted)
- Maintain the hierarchical structure of the original configuration
- Preserve the parent object's attributes while including only the selected child objects

This feature is especially useful when you need to:
- Generate configuration snippets with related objects
- Apply the same status to groups of related objects
- Create template configurations with specific object combinations

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
