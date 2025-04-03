# APIC Parser

APIC Parser is a Python-based tool for parsing and searching through Cisco ACI APIC (Application Policy Infrastructure Controller) JSON configuration files.

## Features

- Parse large APIC JSON configuration files using a streaming parser
- Extract top-level objects from the tenant configuration
- Search for specific objects by type and name
- Search for multiple objects in a single command
- Set status attributes for objects (create or delete)
- Output results in the standard APIC JSON format
- Save search results to files
- User-friendly web interface with Streamlit

## Prerequisites

- Python 3.6+
- Required libraries:
  - ijson (for streaming JSON parsing)
  - streamlit (for the web interface)
  - pandas (for data display in the web interface)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

#### Basic Usage

```bash
python main.py -f <path_to_json_file>
```

#### Command-line Options

- `-f, --file`: Path to the APIC JSON configuration file to parse (default: tn-Datacenter1.json)
- `-t, --top-level`: Display top-level objects from the APIC JSON file
- `--find-object`: Find object(s) by type and name
- `--object-type`: Type of object to find (e.g., "fvBD")
- `--object-name`: Name of object to find (e.g., "BD_484") or a comma-separated list (e.g., "BD_484,BD_721")
- `--output-file`: Save the found object(s) to this file path
- `--set-status`: Set status for the found objects (`create` or `delete`)

#### Examples

##### View Top-level Objects

```bash
python main.py -f tn-Datacenter1.json --top-level
```

##### Find a Single Object

```bash
python main.py --find-object --object-type "fvBD" --object-name "BD_484"
```

##### Find Multiple Objects

```bash
python main.py --find-object --object-type "fvBD" --object-name "BD_484,BD_721"
```

##### Save Results to a File

```bash
python main.py --find-object --object-type "fvBD" --object-name "BD_484,BD_721" --output-file "result.json"
```

##### Set Objects to Deleted Status

```bash
python main.py --find-object --object-type "fvBD" --object-name "BD_484,BD_721" --set-status delete --output-file "result.json"
```

##### Set Objects to Created Status

```bash
python main.py --find-object --object-type "fvBD" --object-name "BD_484,BD_721" --set-status create --output-file "result.json"
```

### Web Interface

The project includes a user-friendly web interface built with Streamlit.

#### Starting the Web App

```bash
streamlit run app.py
```

#### Using the Web App

1. Upload an APIC JSON file using the sidebar
2. Navigate through the tabs to:
   - View top-level objects in the Overview tab
   - Search for specific objects in the Search tab
   - Set object status (create/modified or deleted) in the Search tab
   - Download the results as a JSON file

## Output Format

The output follows the standard APIC format with objects properly nested within the tenant structure:

```json
{
  "totalCount": "2",
  "imdata": [
    {
      "fvTenant": {
        "attributes": {
          "name": "Datacenter1",
          "descr": "",
          "dn": "uni/tn-Datacenter1",
          ...
        },
        "children": [
          {
            "fvBD": {
              "attributes": {
                "name": "BD_484",
                "status": "deleted",  // Status attribute can be set
                ...
              },
              "children": [...]
            }
          },
          {
            "fvBD": {
              "attributes": {
                "name": "BD_721",
                "status": "deleted",  // Status attribute can be set
                ...
              },
              "children": [...]
            }
          }
        ]
      }
    }
  ]
}
```

## Status Values

The tool supports setting the status attribute for objects:
- `created,modified`: Used for objects that should be created or updated
- `deleted`: Used for objects that should be deleted

## Project Structure

```
APIC_Parser/
├── main.py                  # Command-line interface entry point
├── app.py                   # Streamlit web interface
├── apic_parser/
│   └── apic_parser.py       # Core parsing and search functionality
├── requirements.txt         # Dependencies for the project
├── README.md                # Documentation
├── nested_object.json       # Cached parsed JSON data (optional)
├── result.json              # Example output file
└── tn-Datacenter1.json      # Example APIC configuration file
```

## How It Works

1. The tool uses `ijson` to parse APIC JSON files in a streaming manner, which allows it to efficiently handle large files
2. When searching for objects, the tool traverses the parsed data structure using an iterative depth-first search approach
3. Results are wrapped in the standard APIC format, preserving the tenant structure and attributes
4. Status attributes can be set to either "created,modified" or "deleted" as needed for APIC configuration

## Extending the Tool

To add support for more search capabilities:

1. Add new functions to `apic_parser.py`
2. Update the CLI interface in `main.py` and/or the web interface in `app.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.