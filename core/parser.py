import json

def load_config(file_path):
    """Load JSON configuration from file"""
    with open(file_path, 'r') as f:
        return json.load(f)


def extract_object(node, target_class, result=None):
    if result is None:
        result = []
    
    # If node is a list, process each item
    if isinstance(node, list):
        for item in node:
            extract_object(item, target_class, result)
        return result
        
    # Process dictionary objects
    if isinstance(node, dict):
        for class_name, value in node.items():
            if isinstance(value, dict):
                # If this node matches the target class, add to results
                if class_name == target_class:
                    attributes = value.get('attributes', {})
                    # children = value.get('children', [])

                    entry = {
                        "class": class_name,
                        "attributes": attributes,
                        "children": []
                    }
                    result.append(entry)
                    
                    # Add all children regardless of class
                    children = value.get('children', [])
                    if children:
                        for child in children:
                            for child_class, child_value in child.items():
                                child_entry = {
                                    "class": child_class,
                                    "attributes": child_value.get('attributes', {}),
                                    "children": []
                                }
                                
                                # Recursively extract children of this child
                                if child_value.get('children'):
                                    # Extract all children recursively regardless of class
                                    child_children = []
                                    for grandchild in child_value.get('children'):
                                        for gc_class, gc_value in grandchild.items():
                                            gc_entry = {
                                                "class": gc_class,
                                                "attributes": gc_value.get('attributes', {}),
                                                "children": []
                                            }
                                            # Process deeper children if they exist
                                            if gc_value.get('children'):
                                                extract_object(gc_value.get('children'), None, gc_entry['children'])
                                            child_children.append(gc_entry)
                                    
                                    # print(child_children)
                                    child_entry['children'] = child_children
                                
                                entry['children'].append(child_entry)
                else:
                    # Recursively process children even if current class doesn't match
                    children = value.get('children', [])
                    if children:
                        for child in children:
                            extract_object(child, target_class, result)
    
    return result        



if __name__ == "__main__":
    config = load_config(r"C:\Users\dsu979\OneDrive - dynexo GmbH\Desktop\APIC\tn-Datacenter1.json")
    
    # Start from the root tenant object
    tenant_node = config['imdata'][0]['fvTenant']["children"]
    
    # Extract all objects of class 'fvBD' (Bridge Domains)
    bds = extract_object(tenant_node, 'fvAp')
    print(bds)

    print(f"Found {len(bds)} Bridge Domains")
    for bd in bds:  # Show first 2 as example
        print(f"- Name: {bd['attributes']['name']}")
        print(f"  Children: {[child['class'] for child in bd['children']]}")
