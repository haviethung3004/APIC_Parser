# APIC Parser

A Python tool for parsing and extracting objects from Cisco ACI (Application Centric Infrastructure) configuration files.

## Overview

APIC Parser is designed to help network administrators and automation engineers extract and manipulate Cisco ACI configuration objects from JSON exports. It provides functionality to:

- Parse and analyze ACI configuration files
- Extract specific child objects by index
- Search for objects by class name
- Generate summaries of configuration hierarchies
- Export configurations to separate files

## Installation

No installation is required. Simply clone or download the repository and ensure you have Python 3.6+ installed.

```bash
git clone <repository-url>
cd APIC_Parser
```

## Usage

### Basic Usage

```bash
python apic_parser.py [OPTIONS]
```

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file FILE` | `-f FILE` | Path to the configuration file |
| `--child INDEX` | `-c INDEX` | Index of child to extract (0-based) |
| `--output FILE` | `-o FILE` | Output file path for extracted configuration |
| `--summary` | `-s` | Show summary only |
| `--list` | `-l` | List all children |
| `--class CLASS` | `-cls CLASS` | Search for objects of a specific class |
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

4. Save a child object to a separate file:

```bash
python apic_parser.py -f your_config.json -c 9 -o child9.json
```

5. Search for objects of a specific class:

```bash
python apic_parser.py -f your_config.json --class fvBD
```

## Project Structure

```
APIC_Parser/
├── apic_parser.py       # Main entry point script
├── README.md           # This file
├── core/               # Core functionality
│   ├── __init__.py
│   ├── extractors.py   # Object extraction logic
│   ├── models.py       # Data models for ACI objects
│   └── parser.py       # Main parser implementation
└── utils/              # Utility modules
    └── file_utils.py   # File handling utilities
```

## Core Components

- **ACIConfigParser**: Main class for parsing and analyzing configuration files
- **ACIObjectExtractor**: Handles the extraction of objects from the configuration hierarchy
- **ACIObject**: Data model representing an ACI object with its attributes and children
- **TenantConfig**: Represents a full tenant configuration with its child objects

## Development

### Dependencies

- Python 3.6+
- Standard library only (no external dependencies)

### Extending the Parser

To add new functionality:

1. Add new methods to the `ACIConfigParser` class in `core/parser.py`
2. Update the command-line interface in the `main()` function
3. Add any new utility functions to the appropriate modules

## License

[Specify your license here]
