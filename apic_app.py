#!/usr/bin/env python3
"""
APIC Parser - Streamlit Web Application
Run this script with 'streamlit run apic_app.py' to launch the web interface
"""
import os
import json
import tempfile
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
import sys
import base64

# Add the current directory to the path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our custom modules
from core.parser import ACIConfigParser
from utils.file_utils import load_json_config, save_json_config

# Set page configuration
st.set_page_config(
    page_title="APIC Parser",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper functions
def create_download_link(data, filename, text):
    """Create a download link for a file"""
    json_str = json.dumps(data, indent=2)
    b64 = base64.b64encode(json_str.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="{filename}">{text}</a>'
    return href

def load_file_from_upload(uploaded_file):
    """Load configuration from uploaded file"""
    # Save uploaded file to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    # Create parser and load the config
    parser = ACIConfigParser(tmp_path)
    if parser.load():
        st.session_state.parser = parser
        st.session_state.config_file = tmp_path
        st.session_state.filename = uploaded_file.name
        return True
    else:
        # Clean up temp file if loading failed
        os.unlink(tmp_path)
        return False

def format_attributes_table(attributes):
    """Format attributes for display in a table"""
    if not attributes:
        return pd.DataFrame()
    
    # Create dataframe from attributes
    df = pd.DataFrame(list(attributes.items()), columns=['Attribute', 'Value'])
    return df

def render_object_details(obj):
    """Render details for a specific object"""
    with st.expander(f"Class: {obj['class']} | Name: {obj['attributes'].get('name', 'N/A')}", expanded=False):
        # Main attributes
        st.subheader("Attributes")
        st.dataframe(format_attributes_table(obj['attributes']), use_container_width=True)
        
        # Children summary
        if obj['children']:
            st.subheader(f"Children ({len(obj['children'])} objects)")
            for i, child in enumerate(obj['children']):
                child_name = child['attributes'].get('name', f"Child {i}")
                child_class = child['class']
                child_status = child['attributes'].get('status', 'N/A')
                st.write(f"- {child_name} ({child_class}) | Status: {child_status}")

def save_and_download_config(parser, output_filename):
    """Save configuration and provide download link"""
    try:
        temp_file = os.path.join(tempfile.gettempdir(), output_filename)
        if parser.save_config(temp_file):
            with open(temp_file, 'r') as f:
                config_data = json.load(f)
            st.success(f"Configuration saved successfully!")
            st.markdown(
                create_download_link(config_data, output_filename, "Download JSON file"),
                unsafe_allow_html=True
            )
            return True
        else:
            st.error("Failed to save configuration.")
            return False
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")
        return False

def render_nested_object_tree(hierarchy, selected_paths):
    """Render a nested object tree with checkboxes for selection"""
    if not hierarchy:
        return []

    for i, item in enumerate(hierarchy):
        parent_id = f"batch_root_{i}"
        parent_path = item['path']
        parent_text = f"{item['class']} - {item['name']}"
        parent_selected = parent_path in selected_paths
        
        if st.checkbox(parent_text, value=parent_selected, key=parent_id):
            if parent_path not in selected_paths:
                selected_paths.append(parent_path)
        elif parent_path in selected_paths:
            selected_paths.remove(parent_path)
            
        # Process children with indentation
        if item['children']:
            render_children_tree(item['children'], selected_paths, 1)

    return selected_paths

def render_children_tree(children, selected_paths, level=1):
    """Helper function to render children in the tree view"""
    for i, child in enumerate(children):
        child_id = f"batch_child_{level}_{i}_{child['path']}"
        child_path = child['path']
        status_info = f" | Status: {child['status']}" if child.get('status', 'None') != 'None' else ""
        # Use spacing for indentation instead of nested columns
        indent = "&nbsp;" * (level * 4)
        child_text = f"{child['class']} - {child['name']}{status_info}"
        st.markdown(f"{indent}", unsafe_allow_html=True)
        child_selected = child_path in selected_paths
        
        if st.checkbox(child_text, value=child_selected, key=child_id):
            if child_path not in selected_paths:
                selected_paths.append(child_path)
        elif child_path in selected_paths:
            selected_paths.remove(child_path)
            
        # Recursively process grandchildren if any
        if child.get('children'):
            render_children_tree(child['children'], selected_paths, level + 1)

# Sidebar for file selection and general options
st.sidebar.title("APIC Parser")
st.sidebar.image("https://www.cisco.com/c/dam/assets/swa/img/anchor-images/cloud-networking-aci-anchor.jpg", width=100)

# File upload
uploaded_file = st.sidebar.file_uploader("Upload ACI JSON Configuration", type=["json"])

# Sample files option
sample_file = st.sidebar.selectbox(
    "Or select a sample file:",
    ["None", "tn-Datacenter1.json"]
)

# Initialize session state for parser
if "parser" not in st.session_state:
    st.session_state.parser = None
    st.session_state.config_file = None
    st.session_state.filename = None

# Initialize selected paths session state
if "selected_paths" not in st.session_state:
    st.session_state.selected_paths = []

# Handle file upload
if uploaded_file is not None:
    if load_file_from_upload(uploaded_file):
        st.sidebar.success(f"Loaded: {uploaded_file.name}")
    else:
        st.sidebar.error("Failed to load configuration file.")

# Handle sample file selection
elif sample_file != "None":
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), sample_file)
    if os.path.exists(sample_path):
        parser = ACIConfigParser(sample_path)
        if parser.load():
            st.session_state.parser = parser
            st.session_state.config_file = sample_path
            st.session_state.filename = sample_file
            st.sidebar.success(f"Loaded: {sample_file}")
        else:
            st.sidebar.error("Failed to load sample file.")
    else:
        st.sidebar.error(f"Sample file not found: {sample_path}")

# Navigation menu
if st.session_state.parser:
    nav_option = st.sidebar.radio(
        "Navigate:",
        ["Summary", "Child Objects", "Nested Objects", "Extract & Modify", "Class Search"]
    )
else:
    st.title("APIC Parser")
    st.write("### Welcome to the APIC Parser Web Interface")
    st.write("Please upload a JSON configuration file or select a sample file from the sidebar to begin.")
    st.image("https://www.cisco.com/c/dam/en/us/td/i/300001-400000/390001-400000/398001-399000/398085.jpg", width=800)
    nav_option = None

# Main content area
if nav_option == "Summary":
    st.title(f"Configuration Summary: {st.session_state.filename}")
    
    parser = st.session_state.parser
    objects = parser.objects
    
    # Basic stats
    if objects:
        # Get the first object (typically imdata)
        main_obj = objects[0]
        children_count = len(main_obj['children'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Objects", len(objects))
        col2.metric("Child Objects", children_count)
        
        # Count classes
        class_counts = {}
        for child in main_obj['children']:
            class_name = child['class']
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        col3.metric("Unique Classes", len(class_counts))
        
        # Class distribution chart
        if class_counts:
            st.subheader("Object Class Distribution")
            df = pd.DataFrame(list(class_counts.items()), columns=['Class', 'Count'])
            df = df.sort_values('Count', ascending=False)
            
            # Plot chart
            st.bar_chart(df.set_index('Class'))
            
        # Show the main object details
        st.subheader("Root Object Details")
        render_object_details(main_obj)
            
        # Option to show JSON
        if st.checkbox("Show Raw JSON"):
            st.json(parser.config)
    else:
        st.warning("No objects found in the configuration.")

elif nav_option == "Child Objects":
    st.title(f"Child Objects: {st.session_state.filename}")
    
    parser = st.session_state.parser
    
    if parser.objects and parser.objects[0]['children']:

        children = parser.objects[0]['children']
        
        # Create a dataframe for the table view
        records = []
        for i, child in enumerate(children):
            record = {
                'Index': i,
                'Class': child['class'],
                'Name': child['attributes'].get('name', 'N/A'),
                'Description': child['attributes'].get('descr', ''),
                'Status': child['attributes'].get('status', 'N/A'),
                'Children': len(child.get('children', [])),
            }
            records.append(record)
            
        df = pd.DataFrame(records)
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            class_filter = st.multiselect(
                "Filter by Class:",
                options=sorted(df['Class'].unique()),
                default=[]
            )
        
        with col2:
            status_filter = st.multiselect(
                "Filter by Status:",
                options=sorted(df['Status'].unique()),
                default=[]
            )
        
        # Apply filters
        filtered_df = df
        if class_filter:
            filtered_df = filtered_df[filtered_df['Class'].isin(class_filter)]
        if status_filter:
            filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]
            
        # Display table
        st.dataframe(filtered_df, use_container_width=True)
        
        # Details view for selected object
        selected_index = st.selectbox(
            "Select object to view details:",
            options=filtered_df['Index'].tolist(),
            format_func=lambda x: f"{x}: {df.loc[df['Index'] == x, 'Class'].iloc[0]} - {df.loc[df['Index'] == x, 'Name'].iloc[0]}"
        )
        
        if selected_index is not None:
            child = children[selected_index]
            st.subheader(f"Object Details: {child['attributes'].get('name', f'Object {selected_index}')}")

            # Show attributes
            st.write("#### Attributes")
            st.dataframe(format_attributes_table(child['attributes']), use_container_width=True)
            
            # Show children if any
            if child.get('children'):
                st.write(f"#### Children ({len(child['children'])})")
                for i, grandchild in enumerate(child['children']):
                    gc_name = grandchild['attributes'].get('name', f"Child {i}")
                    gc_class = grandchild['class']
                    st.write(f"- {gc_name} ({gc_class})")
                    
            # Show JSON option
            if st.checkbox("Show Raw JSON"):
                st.json(child)
    else:
        st.warning("No child objects found in the configuration.")

elif nav_option == "Nested Objects":
    st.title(f"Nested Objects: {st.session_state.filename}")
    
    parser = st.session_state.parser
    
    # Get the full object hierarchy
    hierarchy = parser.get_object_hierarchy()
    
    if hierarchy:
        st.write("### Object Hierarchy")
        st.write("Navigate through the nested object structure. Click on any object to view its details.")
        
        # Left column for tree view, right for details
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("#### Object Tree")
            # Use session state to maintain selection state between renders
            selected_object_path = None
            
            # Create a simple tree representation without nested columns
            for i, root_obj in enumerate(hierarchy):
                root_expanded = st.checkbox(f"{root_obj['class']} - {root_obj['name']}", key=f"tree_root_{i}")
                
                if root_expanded:
                    # Display children with indentation
                    def render_tree(children, level=1, parent_path=None):
                        for j, child in enumerate(children):
                            child_path = child['path']
                            status_badge = ""
                            if child.get('status', 'None') not in ('None', 'N/A'):
                                status = child['status']
                                color = "red" if status == "deleted" else "green" if status == "created" else "orange"
                                status_badge = f" <span style='color:{color}'>[{status}]</span>"
                            
                            # Use HTML spacing for indentation instead of nested columns
                            indent = "&nbsp;" * (level * 4)
                            st.markdown(f"{indent}", unsafe_allow_html=True)
                                
                            child_key = f"tree_node_{level}_{j}_{child_path}"
                            child_selected = st.button(
                                f"• {child['class']} - {child['name']}{status_badge}", 
                                key=child_key,
                                help=f"Path: {child_path}"
                            )
                            
                            if child_selected:
                                selected_object_path = child_path
                                st.session_state.selected_obj_path = child_path
                                
                            # Recursively render any children
                            if child.get('children'):
                                render_tree(child['children'], level + 1, child_path)
                    
                    # Render children starting with level 1
                    render_tree(root_obj['children'])
        
        # Right column for object details
        with col2:
            st.write("#### Object Details")
            
            # Check if an object is selected from the tree
            selected_path = st.session_state.get('selected_obj_path', None)
            if selected_path:
                # Get the object configuration
                obj_config = parser.get_nested_child_config(selected_path)
                
                if obj_config:
                    # Extract class name and attributes
                    obj_class = list(obj_config.keys())[0]
                    obj_data = obj_config[obj_class]
                    attributes = obj_data.get('attributes', {})
                    
                    # Display object information
                    st.subheader(f"{obj_class}")
                    if 'name' in attributes:
                        st.write(f"**Name:** {attributes['name']}")
                    
                    # Status information
                    current_status = attributes.get('status', 'None')
                    status_color = "red" if current_status == "deleted" else "green" if current_status == "created" else "orange" if "modified" in str(current_status) else "gray"
                    st.write(f"**Current Status:** <span style='color:{status_color};font-weight:bold'>{current_status}</span>", unsafe_allow_html=True)
                    
                    # Status modification options
                    st.write("### Modify Status")
                    new_status = st.selectbox(
                        "Set new status:",
                        options=["No change", "created", "modified, created", "deleted", "None (remove status)"],
                        key=f"status_{selected_path}"
                    )
                    
                    if st.button("Apply Status Change"):
                        if new_status != "No change":
                            status_value = None if new_status == "None (remove status)" else new_status
                            if parser.set_nested_child_status(selected_path, status_value):
                                st.success(f"Status updated to: {status_value or 'None'}")
                                # Refresh hierarchy
                                hierarchy = parser.get_object_hierarchy()
                            else:
                                st.error("Failed to update status")
                        else:
                            st.info("No status change requested")
                    
                    # Attributes table
                    st.write("### Attributes")
                    st.dataframe(format_attributes_table(attributes), use_container_width=True)
                    
                    # Children summary
                    if 'children' in obj_data and obj_data['children']:
                        children = obj_data['children']
                        st.write(f"### Children ({len(children)})")
                        for i, child in enumerate(children):
                            child_class = list(child.keys())[0]
                            child_attrs = child[child_class].get('attributes', {})
                            child_name = child_attrs.get('name', f"Child {i}")
                            child_status = child_attrs.get('status', 'None')
                            st.write(f"- {child_name} ({child_class}) | Status: {child_status}")
                    
                    # Show JSON option
                    if st.checkbox("Show Raw JSON"):
                        st.json(obj_config)
                else:
                    st.warning(f"Could not retrieve configuration for object at path {selected_path}")
            else:
                st.info("Select an object from the tree to view details")

        # Batch operations section
        st.write("### Batch Operations")
        st.write("Select multiple objects from the hierarchy and perform operations.")
        
        # Create the selection tree
        selected_paths = render_nested_object_tree(hierarchy, st.session_state.selected_paths)
        st.session_state.selected_paths = selected_paths
        
        if selected_paths:
            st.write(f"Selected {len(selected_paths)} objects")
            
            # Batch status update
            status_options = ["created", "modified, created", "deleted", "None (remove status)"]
            batch_status = st.selectbox("Set status for all selected objects:", options=status_options)
            
            if st.button("Apply Batch Status Change"):
                status_value = None if batch_status == "None (remove status)" else batch_status
                if parser.set_multiple_nested_children_status(selected_paths, status_value):
                    st.success(f"Status updated to '{status_value or 'None'}' for all selected objects")
                    # Refresh hierarchy and clear selections
                    hierarchy = parser.get_object_hierarchy()
                    st.session_state.selected_paths = []
                else:
                    st.error("Failed to update status for some or all objects")
            
            # Extract selected objects
            if st.button("Extract Selected Objects"):
                output_filename = f"selected_objects_{len(selected_paths)}.json"
                if parser.extract_multiple_nested_children_to_file(selected_paths, os.path.join(tempfile.gettempdir(), output_filename)):
                    with open(os.path.join(tempfile.gettempdir(), output_filename), 'r') as f:
                        extracted_data = json.load(f)
                    st.success(f"{len(selected_paths)} objects extracted successfully!")
                    st.markdown(
                        create_download_link(extracted_data, output_filename, "Download JSON file"),
                        unsafe_allow_html=True
                    )
                else:
                    st.error("Failed to extract objects")
    else:
        st.warning("No object hierarchy found in the configuration.")

elif nav_option == "Extract & Modify":
    st.title(f"Extract & Modify: {st.session_state.filename}")
    
    parser = st.session_state.parser
    
    if parser.objects and parser.objects[0]['children']:
        children = parser.objects[0]['children']
        
        # Create simple list for selection
        options = []
        for i, child in enumerate(children):
            name = child['attributes'].get('name', f"Object {i}")
            class_name = child['class']
            status = child['attributes'].get('status', 'None')
            options.append(f"{i}: {class_name} - {name} | Status: {status}")
        
        # Selection mode
        selection_mode = st.radio(
            "Selection mode:",
            ["Single Object", "Multiple Objects"]
        )

        # Status options
        status_options = [
            "No change",
            "created", 
            "modified, created", 
            "deleted", 
            "None (remove status)"
        ]
        
        if selection_mode == "Single Object":
            selected = st.selectbox(
                "Select object:",
                options=options
            )
            
            if selected:
                index = int(selected.split(':')[0])
                
                # Preview the selected object
                with st.expander("Preview", expanded=True):
                    child_config = parser.get_child_config(child_index=index)
                    if child_config:
                        st.json(child_config)
                
                # Status modification
                col1, col2 = st.columns(2)
                
                with col1:
                    new_status = st.selectbox(
                        "Set status (optional):",
                        options=status_options
                    )
                
                with col2:
                    output_filename = st.text_input("Output filename:", f"object_{index}.json")
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Extract Object"):
                        # First update status if requested
                        if new_status != "No change":
                            status_value = None if new_status == "None (remove status)" else new_status
                            parser.set_child_status(index, status_value)
                            st.success(f"Status set to: {status_value or 'None'}")
                        
                        # Then extract to file
                        temp_file = os.path.join(tempfile.gettempdir(), output_filename)
                        if parser.extract_child_to_file(index, temp_file):
                            with open(temp_file, 'r') as f:
                                object_data = json.load(f)
                            st.success(f"Object extracted successfully!")
                            st.markdown(
                                create_download_link(object_data, output_filename, "Download JSON file"),
                                unsafe_allow_html=True
                            )
                        else:
                            st.error("Failed to extract object.")
                
                with col2:
                    if st.button("Save to Original Config"):
                        if new_status != "No change":
                            status_value = None if new_status == "None (remove status)" else new_status
                            if parser.set_child_status(index, status_value):
                                st.success(f"Status updated to: {status_value or 'None'}")
                                save_and_download_config(parser, st.session_state.filename)
                            else:
                                st.error("Failed to update status")
                        else:
                            st.info("No changes to save")
                
        else:  # Multiple Objects
            selected_indices = st.multiselect(
                "Select objects:",
                options=options
            )
            
            if selected_indices:
                indices = [int(option.split(':')[0]) for option in selected_indices]
                
                # Preview the combined objects
                with st.expander(f"Preview ({len(indices)} objects selected)", expanded=True):
                    # Get the combined configuration
                    combined_config = parser.get_multiple_children_config(indices)
                    if combined_config:
                        st.json(combined_config)
                
                # Status modification
                col1, col2 = st.columns(2)
                
                with col1:
                    new_status = st.selectbox(
                        "Set status for all selected objects (optional):",
                        options=status_options
                    )
                
                with col2:
                    output_filename = st.text_input(
                        "Output filename:", 
                        f"objects_{'-'.join(str(i) for i in indices)}.json"
                    )
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Extract Objects"):
                        # First update status if requested
                        if new_status != "No change":
                            status_value = None if new_status == "None (remove status)" else new_status
                            parser.set_multiple_children_status(indices, status_value)
                            st.success(f"Status set to: {status_value or 'None'} for all selected objects")
                        
                        # Then extract to file
                        temp_file = os.path.join(tempfile.gettempdir(), output_filename)
                        if parser.extract_multiple_children_to_file(indices, temp_file):
                            with open(temp_file, 'r') as f:
                                combined_data = json.load(f)
                            st.success(f"{len(indices)} objects extracted successfully!")
                            st.markdown(
                                create_download_link(combined_data, output_filename, "Download JSON file"),
                                unsafe_allow_html=True
                            )
                        else:
                            st.error("Failed to extract objects.")
                
                with col2:
                    if st.button("Save to Original Config"):
                        if new_status != "No change":
                            status_value = None if new_status == "None (remove status)" else new_status
                            if parser.set_multiple_children_status(indices, status_value):
                                st.success(f"Status updated to: {status_value or 'None'} for all selected objects")
                                save_and_download_config(parser, st.session_state.filename)
                            else:
                                st.error("Failed to update status for some or all objects")
                        else:
                            st.info("No changes to save")
    else:
        st.warning("No child objects found in the configuration.")

elif nav_option == "Class Search":
    st.title(f"Class Search: {st.session_state.filename}")
    
    parser = st.session_state.parser
    
    # Get unique classes from children
    unique_classes = set()
    if parser.objects and parser.objects[0]['children']:
        for child in parser.objects[0]['children']:
            unique_classes.add(child['class'])
    
    # Class selection
    selected_class = st.selectbox(
        "Search for objects of class:",
        options=sorted(list(unique_classes))
    )
    
    if selected_class and st.button("Search"):
        objects = parser.get_objects_by_class(selected_class)
        st.write(f"Found {len(objects)} objects of class '{selected_class}'")
        
        # Display results
        for i, obj in enumerate(objects):
            with st.expander(f"Object {i+1}: {obj['attributes'].get('name', f'Unnamed {selected_class}')}"):
                st.write("#### Attributes")
                st.dataframe(format_attributes_table(obj['attributes']), use_container_width=True)
                
                # Children
                if obj['children']:
                    st.write(f"#### Children ({len(obj['children'])})")
                    for j, child in enumerate(obj['children']):
                        child_name = child['attributes'].get('name', f"Child {j}")
                        child_class = child['class']
                        st.write(f"- {child_name} ({child_class})")
        
        # Option for JSON output
        if objects and st.checkbox("Show Raw JSON"):
            st.json(objects)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("APIC Parser - Web Interface")