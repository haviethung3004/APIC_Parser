import ijson
from typing import AnyStr, List, Dict, Optional

def parse_apic_json(json_file_path: AnyStr) -> List[str]:
    """
    Parse the APIC JSON file and extract 'name' attributes from 'fvTenant' children.
    Uses ijson for memory-efficient incremental parsing.
    
    Args:
        json_file_path (AnyStr): Path to the JSON file.
    
    Returns:
        List[str]: A list of all 'name' attributes found in 'children'.
    """
    names = []
    
    with open(json_file_path, 'rb') as file:
        # Navigate to the tenant children level
        tenants = ijson.items(file, 'imdata.item.fvTenant')
        
        for tenant in tenants:
            if 'children' in tenant:
                for child in tenant['children']:
                    # Extract the object type and data
                    names.append(next(iter(child)))
        
        print(set(names))
    
    return names

if __name__ == "__main__":
    json_file_path = r'C:\Users\Viet Hung\Documents\APIC_Parser\tn-Migrate1.json'
    parsed_data = parse_apic_json(json_file_path)
    
