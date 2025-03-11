"""
APIC Parser - Streamlit Web Interface
"""
import streamlit as st
import sys
import json
import os
import pandas as pd
from typing import Dict, List, Any, Optional

# Import from our modules
# Adjust import paths as needed
from core.parser import ACIConfigParser

st.set_page_config(
    page_title="APIC Parser",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit application"""
    
    st.title("APIC Parser")
    st.subheader("Cisco ACI Configuration Management Tool")
    
    # Sidebar for file selection and actions
    with st.sidebar:
        st.header("Configuration")
        uploaded_file = st.file_uploader("Upload ACI Configuration File", type=["json"])
        
        if uploaded_file:
            # Save the uploaded file temporarily to work with it
            with open("temp_config.json", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Create parser and load configuration
            parser = ACIConfigParser("temp_config.json")
            if parser.load():
                st.success(f"Successfully loaded configuration from {uploaded_file.name}")
                st.session_state['parser'] = parser
                st.session_state['file_name'] = uploaded_file.name
            else:
                st.error("Failed to load configuration file")
        
        # Sample files option
        st.subheader("Or use sample file:")
        sample_files = ["tn-Datacenter1.json", "Database1.json"] 
        selected_sample = st.selectbox("Select sample file", sample_files, index=0)
        
        if st.button("Load Sample"):
            # Create parser and load sample configuration
            parser = ACIConfigParser(selected_sample)
            if parser.load():
                st.success(f"Successfully loaded sample: {selected_sample}")
                st.session_state['parser'] = parser
                st.session_state['file_name'] = selected_sample
            else:
                st.error(f"Failed to load sample: {selected_sample}")
        
        # Actions section
        st.header("Actions")
        action = st.radio("Select Action", 
                         ["View Summary", "List All Children", "Extract Child", 
                          "Search by Class", "Set Child Status"])
        
        # Apply selected action
        if 'parser' in st.session_state and st.button("Apply Action"):
            st.session_state['selected_action'] = action
    
    # Main content area
    if 'parser' in st.session_state:
        parser = st.session_state['parser']
        
        # Show current file info
        st.info(f"Currently working with: {st.session_state.get('file_name', 'Unknown file')}")
        
        # Handle different actions
        action = st.session_state.get('selected_action', None)
        
        if action == "View Summary":
            display_summary(parser)
        
        elif action == "List All Children":
            list_all_children(parser)
        
        elif action == "Extract Child":
            extract_child(parser)
        
        elif action == "Search by Class":
            search_by_class(parser)
        
        elif action == "Set Child Status":
            set_child_status(parser)

def display_summary(parser: ACIConfigParser):
    """Display a summary of the configuration"""
    st.header("Configuration Summary")
    
    # Extract basic info about the config
    obj_count = len(parser.objects)
    st.write(f"Found {obj_count} total objects")
    
    # Show first level object info
    if parser.objects:
        obj = parser.objects[0]
        st.subheader(f"Root Object: {obj['class']}")
        st.write(f"Path: {obj['path']}")
        
        # Display attributes in a table
        if obj['attributes']:
            st.write(f"Attributes: {len(obj['attributes'])} keys")
            attrs_df = pd.DataFrame({"Key": list(obj['attributes'].keys()), 
                                    "Value": list(obj['attributes'].values())})
            st.dataframe(attrs_df, use_container_width=True)
        
        # Display children count
        st.write(f"Children: {len(obj['children'])}")
        
        # Show a chart of child classes
        if obj['children']:
            child_classes = {}
            for child in obj['children']:
                child_class = child['class']
                if child_class in child_classes:
                    child_classes[child_class] += 1
                else:
                    child_classes[child_class] = 1
            
            # Create child classes chart
            classes_df = pd.DataFrame({
                "Class": list(child_classes.keys()),
                "Count": list(child_classes.values())
            })
            st.subheader("Child Objects by Class")
            st.bar_chart(classes_df.set_index("Class"))

def list_all_children(parser: ACIConfigParser):
    """List all children in the configuration"""
    st.header("All Child Objects")
    
    if parser.objects and parser.objects[0]['children']:
        children = parser.objects[0]['children']
        
        # Create a dataframe for the children
        child_data = []
        for i, child in enumerate(children):
            child_entry = {
                "Index": i,
                "Class": child['class'],
                "Name": child['attributes'].get('name', 'N/A'),
                "Description": child['attributes'].get('descr', 'N/A'),
                "Status": child['attributes'].get('status', 'N/A'),
                "Child Count": len(child.get('children', []))
            }
            child_data.append(child_entry)
        
        children_df = pd.DataFrame(child_data)
        st.dataframe(children_df, use_container_width=True)
        
        # Add option to view child details
        selected_child_idx = st.number_input("Select child index to view details", 
                                            min_value=0, max_value=len(children)-1, value=0)
        
        if st.button("View Child Details"):
            show_child_details(parser, selected_child_idx)
    else:
        st.warning("No children found in the configuration")

def extract_child(parser: ACIConfigParser):
    """Extract a specific child from the configuration"""
    st.header("Extract Child Object")
    
    if parser.objects and parser.objects[0]['children']:
        children = parser.objects[0]['children']
        
        # Child selection
        child_idx = st.number_input("Select child index", 
                                   min_value=0, max_value=len(children)-1, value=0)
        
        # Get child config
        child_config = parser.get_child_config(child_index=child_idx)
        
        if child_config:
            # Get basic child info
            child_class = list(child_config.keys())[0]
            st.subheader(f"Child {child_idx} - Class: {child_class}")
            
            # Get attributes
            if 'attributes' in child_config[child_class]:
                attrs = child_config[child_class]['attributes']
                if 'name' in attrs:
                    st.write(f"Name: {attrs['name']}")
                if 'descr' in attrs:
                    st.write(f"Description: {attrs['descr']}")
                if 'status' in attrs:
                    st.write(f"Status: {attrs['status']}")
            
            # Display the JSON config
            st.subheader("Configuration:")
            st.json(child_config)
            
            # Download option
            if st.button("Download This Child Config"):
                json_str = json.dumps(child_config, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"child_{child_idx}.json",
                    mime="application/json"
                )
    else:
        st.warning("No children found in the configuration")

def search_by_class(parser: ACIConfigParser):
    """Search for objects by class name"""
    st.header("Search by Class")
    
    # Get a list of unique class names from the objects
    class_names = set()
    if parser.objects:
        def collect_classes(obj):
            class_names.add(obj['class'])
            for child in obj.get('children', []):
                collect_classes(child)
        
        for obj in parser.objects:
            collect_classes(obj)
    
    # Class name input
    class_input = st.selectbox("Select class name", sorted(list(class_names))) if class_names else ""
    class_name = st.text_input("Or enter class name manually", value=class_input)
    
    if class_name and st.button("Search"):
        objects = parser.get_objects_by_class(class_name)
        st.write(f"Found {len(objects)} objects of class {class_name}")
        
        # Display the results
        if objects:
            for i, obj in enumerate(objects[:10]):  # Limit to first 10 for readability
                with st.expander(f"Object {i+1}"):
                    st.json(obj)
            
            if len(objects) > 10:
                st.info(f"...and {len(objects) - 10} more")

def set_child_status(parser: ACIConfigParser):
    """Set status attribute for a child object"""
    st.header("Set Status for Child Object")
    
    if parser.objects and parser.objects[0]['children']:
        children = parser.objects[0]['children']
        
        # Create a table of children
        child_data = []
        for i, child in enumerate(children):
            child_entry = {
                "Index": i,
                "Class": child['class'],
                "Name": child['attributes'].get('name', 'N/A'),
                "Description": child['attributes'].get('descr', 'N/A'),
                "Current Status": child['attributes'].get('status', 'N/A'),
            }
            child_data.append(child_entry)
        
        children_df = pd.DataFrame(child_data)
        st.dataframe(children_df, use_container_width=True)
        
        # Child selection
        child_idx = st.number_input("Select child index to modify", 
                                    min_value=0, max_value=len(children)-1, value=0)
        
        # Status selection
        status_options = ["created", "modified, created", "deleted"]
        status = st.selectbox("Select status", status_options)
        
        # Apply status change
        if st.button("Apply Status Change"):
            if parser.set_child_status(child_idx, status):
                st.success(f"Status for child {child_idx} set to '{status}'")
                
                # Save changes option
                if st.button("Save Changes"):
                    output_path = f"modified_{st.session_state.get('file_name', 'config.json')}"
                    if parser.save_config(output_path):
                        st.success(f"Configuration saved to {output_path}")
                        
                        # Download the modified configuration
                        with open(output_path, 'r') as f:
                            st.download_button(
                                label="Download Modified Configuration",
                                data=f.read(),
                                file_name=output_path,
                                mime="application/json"
                            )
                    else:
                        st.error("Failed to save configuration")
            else:
                st.error(f"Failed to set status for child {child_idx}")
    else:
        st.warning("No children found in the configuration")

def show_child_details(parser: ACIConfigParser, child_idx: int):
    """Show details for a specific child"""
    child_config = parser.get_child_config(child_index=child_idx)
    
    if child_config:
        child_class = list(child_config.keys())[0]
        st.subheader(f"Child {child_idx} Details")
        st.write(f"Class: {child_class}")
        
        # Show attributes in a table
        if 'attributes' in child_config[child_class]:
            attrs = child_config[child_class]['attributes']
            st.write("Attributes:")
            attrs_df = pd.DataFrame({"Key": list(attrs.keys()), 
                                    "Value": list(attrs.values())})
            st.dataframe(attrs_df, use_container_width=True)
        
        # Show full JSON
        with st.expander("View Full Configuration"):
            st.json(child_config)
        
        # Show children if any
        if ('children' in child_config[child_class] and 
            child_config[child_class]['children']):
            st.write(f"Child Objects: {len(child_config[child_class]['children'])}")
            
            child_summary = []
            for i, child in enumerate(child_config[child_class]['children']):
                child_class_name = list(child.keys())[0]
                child_attrs = child[child_class_name].get('attributes', {})
                child_entry = {
                    "Index": i,
                    "Class": child_class_name,
                    "Name": child_attrs.get('name', 'N/A'),
                }
                child_summary.append(child_entry)
            
            if child_summary:
                st.dataframe(pd.DataFrame(child_summary), use_container_width=True)

if __name__ == "__main__":
    main()