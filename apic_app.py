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
        object_tabs = st.tabs(["Object Details", "Extract & Modify", "Class Operations", "Children Manager"])
        
        with object_tabs[0]:  # Object Details tab
            # Details view for selected object - use filtered dataframe
            if filtered_df.empty:
                st.info("No objects match the current filters. Please adjust your filter criteria.")
            else:
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
            # Create options list from filtered dataframe
            if filtered_df.empty:
                st.info("No objects match the current filters. Please adjust your filter criteria.")
            else:
                options = []
                for _, row in filtered_df.iterrows():
                    idx = row['Index']
                    name = row['Name']
                    class_name = row['Class']
                    status = row['Status']
                    options.append(f"{idx}: {class_name} - {name} | Status: {status}")
                
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
        
        with object_tabs[2]:  # Class Operations tab
            st.subheader("Class-Based Operations")
            
            # If class filters are already applied, use them
            if class_filter:
                # Use the first class filter if multiple are selected
                default_class = class_filter[0]
                st.write(f"Working with class: **{default_class}** (from filter)")
                
                # Filter the objects by the selected class
                class_filtered_df = filtered_df[filtered_df['Class'] == default_class]
                
                if not class_filtered_df.empty:
                    st.write(f"Found **{len(class_filtered_df)}** objects of class **{default_class}**")
                    
                    # Display the filtered objects
                    st.dataframe(class_filtered_df, use_container_width=True)
                    
                    # Create selection options for objects of this class
                    class_options = []
                    for _, row in class_filtered_df.iterrows():
                        idx = row['Index']
                        name = row['Name']
                        status = row['Status']
                        class_options.append(f"{idx}: {default_class} - {name} | Status: {status}")
                else:
                    st.warning(f"No objects found with class {default_class}")
                    class_options = []
            else:
                # If no class filter applied, allow user to select a class
                selected_class = st.selectbox(
                    "Filter by Class:",
                    options=sorted(df['Class'].unique())
                )
                
                # Filter objects for the selected class but also respect other filters
                base_filtered_df = df
                if status_filter:
                    base_filtered_df = base_filtered_df[base_filtered_df['Status'].isin(status_filter)]
                    
                class_filtered_df = base_filtered_df[base_filtered_df['Class'] == selected_class]
                
                if not class_filtered_df.empty:
                    st.write(f"Found **{len(class_filtered_df)}** objects of class **{selected_class}**")
                    
                    # Display the filtered objects
                    st.dataframe(class_filtered_df, use_container_width=True)
                    
                    # Create selection options for objects of this class
                    class_options = []
                    for _, row in class_filtered_df.iterrows():
                        idx = row['Index']
                        name = row['Name']
                        status = row['Status']
                        class_options.append(f"{idx}: {selected_class} - {name} | Status: {status}")
                else:
                    st.warning(f"No objects found with class {selected_class}")
                    class_options = []
            
            # Continue with the selection and actions if we have options
            if class_options:
                # Selection of specific objects
                selected_indices = st.multiselect(
                    f"Select objects to modify:",
                    options=class_options
                )
                
                if selected_indices:
                    # Extract the indices from the selection
                    indices = [int(option.split(':')[0]) for option in selected_indices]
                    
                    # Preview the combined objects
                    with st.expander(f"Preview ({len(indices)} objects selected)", expanded=True):
                        # Get the combined configuration
                        combined_config = parser.get_multiple_children_config(indices)
                        if combined_config:
                            st.json(combined_config)
                    
                    # Status modification
                    col1, col2 = st.columns(2)
                    
                    class_name = default_class if 'default_class' in locals() else selected_class
                    
                    with col1:
                        class_status = st.selectbox(
                            f"Set status for selected objects:",
                            options=status_options
                        )
                    
                    with col2:
                        class_output_filename = st.text_input(
                            "Output filename:", 
                            f"{class_name}_selected_objects.json"
                        )
                    
                    # Action buttons for selected objects
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"Extract Selected Objects"):
                            # First update status if requested
                            if class_status != "No change":
                                status_value = None if class_status == "None (remove status)" else class_status
                                success = parser.set_multiple_children_status(indices, status_value)
                                if success:
                                    st.success(f"Status set to: {status_value or 'None'} for selected objects")
                                else:
                                    st.warning("Status updates may have been incomplete")
                            
                            # Then extract selected objects to file
                            temp_file = os.path.join(tempfile.gettempdir(), class_output_filename)
                            if parser.extract_multiple_children_to_file(indices, temp_file):
                                with open(temp_file, 'r') as f:
                                    class_data = json.load(f)
                                st.success(f"{len(indices)} objects extracted successfully!")
                                st.markdown(
                                    create_download_link(class_data, class_output_filename, "Download JSON file"),
                                    unsafe_allow_html=True
                                )
                            else:
                                st.error(f"Failed to extract objects")
                    
                    with col2:
                        if st.button(f"Save Changes to Config"):
                            if class_status != "No change":
                                status_value = None if class_status == "None (remove status)" else class_status
                                success = parser.set_multiple_children_status(indices, status_value)
                                
                                if success:
                                    st.success(f"Status updated to: {status_value or 'None'} for selected objects")
                                    save_and_download_config(parser, st.session_state.filename)
                                else:
                                    st.error(f"Failed to update status for some or all selected objects")
                            else:
                                st.info("No changes to save")
                else:
                    st.info(f"Please select one or more objects to perform operations")
            elif class_filter or 'selected_class' in locals():
                st.info("No objects available with the current filters. Please adjust your filter criteria.")
        with object_tabs[3]:  # Children Manager tab
            st.subheader("Manage Children Objects")
            st.write("Create, delete, or modify children within objects")
            
            # Step 1: Select parent object
            if filtered_df.empty:
                st.info("No objects match the current filters. Please adjust your filter criteria.")
            else:
                # Sort filtered objects by the number of children in descending order
                filtered_df_sorted = filtered_df.sort_values('Children', ascending=False)
                
                # Select a parent object
                parent_options = []
                for _, row in filtered_df_sorted.iterrows():
                    idx = row['Index']
                    name = row['Name']
                    class_name = row['Class']
                    children_count = row['Children']
                    parent_options.append(f"{idx}: {class_name} - {name} | Children: {children_count}")
                
                selected_parent = st.selectbox(
                    "Select object with children:",
                    options=parent_options
                )
                
                if selected_parent:
                    parent_index = int(selected_parent.split(':')[0])
                    parent_obj = children[parent_index]
                    parent_name = parent_obj['attributes'].get('name', f'Object {parent_index}')
                    parent_class = parent_obj['class']
                    parent_children_count = len(parent_obj.get('children', []))
                    
                    st.subheader(f"Children of {parent_class} - {parent_name}")
                    st.write(f"Managing {parent_children_count} children objects")
                    
                    # Get children of the selected parent
                    child_children = parser.get_child_children(parent_index)
                    
                    if not child_children:
                        st.info(f"No children found for this {parent_class} object.")
                    else:
                        # Create a dataframe of the children
                        child_records = []
                        for i, child in enumerate(child_children):
                            if child and len(child) == 1:  # Each child should have one key (class)
                                child_class = list(child.keys())[0]
                                child_data = child[child_class]
                                child_attributes = child_data.get('attributes', {})
                                child_children_count = len(child_data.get('children', []))
                                child_records.append({
                                    'Index': i,
                                    'Class': child_class,
                                    'Name': child_attributes.get('name', f"Child {i}"),
                                    'Status': child_attributes.get('status', 'N/A'),
                                    'Children': child_children_count
                                })
                        
                        child_df = pd.DataFrame(child_records)
                        
                        # Display children table
                        st.dataframe(child_df, use_container_width=True)
                        
                        # Child operations section
                        st.subheader("Child Operations")
                        
                        # Create selection options for children
                        child_options = []
                        for _, row in child_df.iterrows():
                            idx = row['Index']
                            name = row['Name']
                            child_class = row['Class']
                            status = row['Status']
                            child_options.append(f"{idx}: {child_class} - {name} | Status: {status}")
                        
                        # Selection mode
                        selection_mode = st.radio(
                            "Selection mode:",
                            ["Single Child", "Multiple Children"]
                        )
                        
                        if selection_mode == "Single Child":
                            # Single child selection
                            selected_child = st.selectbox(
                                "Select child:",
                                options=child_options
                            )
                            
                            if selected_child:
                                child_index = int(selected_child.split(':')[0])
                                
                                # Preview the selected child
                                with st.expander("Preview Child Object", expanded=True):
                                    child_config = parser.get_child_child_config(parent_index, child_index)
                                    if child_config:
                                        st.json(child_config)
                                
                                # Status modification
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    new_status = st.selectbox(
                                        "Set status for this child:",
                                        options=status_options
                                    )
                                
                                # Action buttons
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button("Update Child Status"):
                                        if new_status != "No change":
                                            status_value = None if new_status == "None (remove status)" else new_status
                                            if parser.set_child_child_status(parent_index, child_index, status_value):
                                                st.success(f"Status set to: {status_value or 'None'}")
                                                # Re-save the configuration
                                                save_and_download_config(parser, st.session_state.filename)
                                            else:
                                                st.error("Failed to update child status")
                                        else:
                                            st.info("No changes made")
                        else:
                            # Multiple children selection
                            selected_children = st.multiselect(
                                "Select children:",
                                options=child_options
                            )
                            
                            if selected_children:
                                child_indices = [int(option.split(':')[0]) for option in selected_children]
                                
                                # Preview the combined children
                                with st.expander(f"Preview ({len(child_indices)} children selected)", expanded=True):
                                    combined_config = parser.get_multiple_child_children_config(parent_index, child_indices)
                                    if combined_config:
                                        st.json(combined_config)
                                
                                # Status modification
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    new_status = st.selectbox(
                                        "Set status for selected children:",
                                        options=status_options
                                    )
                                
                                with col2:
                                    output_filename = st.text_input(
                                        "Output filename:", 
                                        f"children_of_{parent_class}_{parent_index}.json"
                                    )
                                
                                # Action buttons
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button("Update Children Status"):
                                        if new_status != "No change":
                                            status_value = None if new_status == "None (remove status)" else new_status
                                            if parser.set_multiple_child_children_status(parent_index, child_indices, status_value):
                                                st.success(f"Status set to: {status_value or 'None'} for all selected children")
                                                # Re-save the configuration
                                                save_and_download_config(parser, st.session_state.filename)
                                            else:
                                                st.error("Failed to update some or all children statuses")
                                        else:
                                            st.info("No changes made")
                                
                                with col2:
                                    if st.button("Extract Selected Children"):
                                        # First update status if requested
                                        if new_status != "No change":
                                            status_value = None if new_status == "None (remove status)" else new_status
                                            if parser.set_multiple_child_children_status(parent_index, child_indices, status_value):
                                                st.success(f"Status set to: {status_value or 'None'} for all selected children")
                                            else:
                                                st.warning("Status updates may have been incomplete")
                                        
                                        # Then extract the selected children to a file
                                        temp_file = os.path.join(tempfile.gettempdir(), output_filename)
                                        success, count = parser.extract_child_children_to_file(parent_index, child_indices, temp_file)
                                        
                                        if success:
                                            with open(temp_file, 'r') as f:
                                                children_data = json.load(f)
                                            st.success(f"{count} children extracted successfully!")
                                            st.markdown(
                                                create_download_link(children_data, output_filename, "Download JSON file"),
                                                unsafe_allow_html=True
                                            )
                                        else:
                                            st.error("Failed to extract children")
    else:
        st.warning("No child objects found in the configuration.")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("APIC Parser - Web Interface")