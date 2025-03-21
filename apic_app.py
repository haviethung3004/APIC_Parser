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

# Sidebar for file selection and general options
st.sidebar.title("APIC Parser")

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
        ["Summary", "Objects & Extraction"]
    )
else:
    st.title("APIC Parser")
    st.write("### Welcome to the APIC Parser Web Interface")
    st.write("Please upload a JSON configuration file or select a sample file from the sidebar to begin.")
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

elif nav_option == "Objects & Extraction":
    st.title(f"Objects & Extraction: {st.session_state.filename}")
    
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
        
        # Status options for modification
        status_options = [
            "No change",
            "created", 
            "modified, created", 
            "deleted", 
            "None (remove status)"
        ]
        
        # Extraction and modification tabs
        object_tabs = st.tabs(["Object Details", "Extract & Modify"])
        
        with object_tabs[0]:  # Object Details tab
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
        
        with object_tabs[1]:  # Extract & Modify tab
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

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("APIC Parser - Web Interface")