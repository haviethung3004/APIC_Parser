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

# Define status options once for reuse
STATUS_OPTIONS = [
    "No change",
    "created", 
    "modified, created", 
    "deleted", 
    "None (remove status)"
]

# Initialize session state
if "parser" not in st.session_state:
    st.session_state.parser = None
    st.session_state.config_file = None
    st.session_state.filename = None
    st.session_state.selected_index = None
    st.session_state.selected_parent = None
    st.session_state.view_mode = "summary"

# Sidebar for file selection and general options
st.sidebar.title("APIC Parser")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload ACI JSON Configuration", type=["json"])

# Handle file upload
if uploaded_file is not None:
    if load_file_from_upload(uploaded_file):
        st.sidebar.success(f"Loaded: {uploaded_file.name}")
    else:
        st.sidebar.error("Failed to load configuration file.")

# Navigation menu in sidebar
if st.session_state.parser:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    
    view_mode = st.sidebar.radio(
        "Select View:",
        ["Summary", "Object Explorer"]
    )
    
    # Store the view mode in session state
    st.session_state.view_mode = view_mode
    
    # Add quick filters in sidebar if in Object Explorer mode
    if view_mode == "Object Explorer":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Quick Filters")
        
        # Get all classes for filtering
        if st.session_state.parser.objects and st.session_state.parser.objects[0]['children']:
            children = st.session_state.parser.objects[0]['children']
            all_classes = sorted(list(set([child['class'] for child in children])))
            
            # Class filter in sidebar
            selected_class = st.sidebar.selectbox(
                "Filter by Class:",
                options=["All Classes"] + all_classes,
                key="sidebar_class_filter"
            )
            
            if selected_class != "All Classes":
                st.session_state.class_filter = selected_class
            else:
                st.session_state.class_filter = None
else:
    # Welcome screen when no file is loaded
    st.title("APIC Parser")
    st.write("### Welcome to the APIC Parser Web Interface")
    st.write("Please upload a JSON configuration file to begin.")
    st.session_state.view_mode = None

# Main content area
if st.session_state.view_mode == "Summary":
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
        if st.checkbox("Show Raw JSON", key="summary_raw_json"):
            st.json(parser.config)
    else:
        st.warning("No objects found in the configuration.")

elif st.session_state.view_mode == "Object Explorer":
    st.title(f"Object Explorer: {st.session_state.filename}")
    
    parser = st.session_state.parser
    
    if parser.objects and parser.objects[0]['children']:
        children = parser.objects[0]['children']
        
        # Create a dataframe for the table view - optimize by collecting all records first
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
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Class filter - preselect if sidebar has selection
            if hasattr(st.session_state, 'class_filter') and st.session_state.class_filter:
                default_class = [st.session_state.class_filter]
            else:
                default_class = []
                
            class_filter = st.multiselect(
                "Filter by Class:",
                options=sorted(df['Class'].unique()),
                default=default_class
            )
        
        with col2:
            # Changed from status_filter to name_filter
            name_filter = st.text_input(
                "Filter by Name:",
                key="name_filter_input"
            )
            
        with col3:
            sort_by = st.selectbox(
                "Sort by:",
                options=["Children (desc)", "Class", "Name", "Status"],
                index=0
            )
        
        # Apply filters
        filtered_df = df
        if class_filter:
            filtered_df = filtered_df[filtered_df['Class'].isin(class_filter)]
        if name_filter:
            # Filter by name using case-insensitive contains
            filtered_df = filtered_df[filtered_df['Name'].str.contains(name_filter, case=False, na=False)]
            
        # Apply sorting
        if sort_by == "Children (desc)":
            filtered_df = filtered_df.sort_values('Children', ascending=False)
        elif sort_by == "Class":
            filtered_df = filtered_df.sort_values('Class')
        elif sort_by == "Name":
            filtered_df = filtered_df.sort_values('Name')
        elif sort_by == "Status":
            filtered_df = filtered_df.sort_values('Status')
            
        # Display table
        st.dataframe(filtered_df, use_container_width=True)
        
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
                children_count = row['Children']
                options.append(f"{idx}: {class_name} - {name} | Status: {status} | Children: {children_count}")
            
            # Object selector
            selected = st.selectbox(
                "Select object to work with:",
                options=options
            )
            
            if selected:
                index = int(selected.split(':')[0])
                child = children[index]
                st.session_state.selected_index = index  # Store the selected index
                
                # Main tabs for working with objects
                operation_tabs = st.tabs(["Object Details", "Modify & Extract", "Children Manager"])
                
                # Object Details tab
                with operation_tabs[0]:
                    st.subheader(f"Object Details: {child['attributes'].get('name', f'Object {index}')}")
                    
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
                    if st.checkbox("Show Raw JSON", key="object_raw_json"):
                        st.json(child)
                
                # Modify & Extract tab - combined functionality from previous tabs
                with operation_tabs[1]:
                    st.subheader(f"Modify & Extract: {child['attributes'].get('name', f'Object {index}')}")
                    
                    # Show object preview
                    with st.expander("Preview Object", expanded=True):
                        child_config = parser.get_child_config(child_index=index)
                        if child_config:
                            st.json(child_config)
                    
                    # Options for single or multiple objects
                    selection_type = st.radio(
                        "Selection type:",
                        ["This Object Only", "Multiple Objects"],
                        key="selection_type"
                    )
                    
                    if selection_type == "This Object Only":
                        # Status modification
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_status = st.selectbox(
                                "Set status (optional):",
                                options=STATUS_OPTIONS,
                                key="single_status"
                            )
                        
                        with col2:
                            output_filename = st.text_input(
                                "Output filename:", 
                                f"{child['class']}_{child['attributes'].get('name', f'object_{index}')}.json",
                                key="single_filename"
                            )
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Extract Object", key="extract_single"):
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
                            if st.button("Save to Original Config", key="save_single"):
                                if new_status != "No change":
                                    status_value = None if new_status == "None (remove status)" else new_status
                                    if parser.set_child_status(index, status_value):
                                        st.success(f"Status updated to: {status_value or 'None'}")
                                        save_and_download_config(parser, st.session_state.filename)
                                    else:
                                        st.error("Failed to update status")
                                else:
                                    st.info("No changes to save")
                    else:
                        # Multiple object selection - class-based approach
                        st.write("#### Select Objects by Class")
                        
                        # Get class of current object
                        current_class = child['class']
                        
                        # Find all objects of the same class
                        same_class_objects = df[df['Class'] == current_class]
                        
                        if len(same_class_objects) > 1:
                            st.write(f"Found **{len(same_class_objects)}** objects of class **{current_class}**")
                            
                            # Create options for objects of this class
                            class_options = []
                            for _, row in same_class_objects.iterrows():
                                idx = row['Index']
                                name = row['Name']
                                status = row['Status']
                                class_options.append(f"{idx}: {current_class} - {name} | Status: {status}")
                            
                            # Pre-select the current object
                            default_selection = [f"{index}: {current_class} - {child['attributes'].get('name', f'Object {index}')} | Status: {child['attributes'].get('status', 'N/A')}"]
                            
                            # Multi-select for objects
                            selected_indices = st.multiselect(
                                "Select objects of the same class:",
                                options=class_options,
                                default=default_selection if default_selection[0] in class_options else []
                            )
                            
                            if selected_indices:
                                indices = [int(option.split(':')[0]) for option in selected_indices]
                                
                                # Preview the combined objects
                                with st.expander(f"Preview ({len(indices)} objects selected)", expanded=True):
                                    combined_config = parser.get_multiple_children_config(indices)
                                    if combined_config:
                                        st.json(combined_config)
                                
                                # Status modification for multiple objects
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    multi_status = st.selectbox(
                                        "Set status for selected objects:",
                                        options=STATUS_OPTIONS,
                                        key="multi_status"
                                    )
                                
                                with col2:
                                    multi_filename = st.text_input(
                                        "Output filename:", 
                                        f"{current_class}_objects.json",
                                        key="multi_filename"
                                    )
                                
                                # Action buttons for multiple objects
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button("Extract Selected Objects", key="extract_multi"):
                                        # First update status if requested
                                        if multi_status != "No change":
                                            status_value = None if multi_status == "None (remove status)" else multi_status
                                            success = parser.set_multiple_children_status(indices, status_value)
                                            if success:
                                                st.success(f"Status set to: {status_value or 'None'} for selected objects")
                                            else:
                                                st.warning("Status updates may have been incomplete")
                                        
                                        # Then extract to file
                                        temp_file = os.path.join(tempfile.gettempdir(), multi_filename)
                                        if parser.extract_multiple_children_to_file(indices, temp_file):
                                            with open(temp_file, 'r') as f:
                                                combined_data = json.load(f)
                                            st.success(f"{len(indices)} objects extracted successfully!")
                                            st.markdown(
                                                create_download_link(combined_data, multi_filename, "Download JSON file"),
                                                unsafe_allow_html=True
                                            )
                                        else:
                                            st.error("Failed to extract objects.")
                                
                                with col2:
                                    if st.button("Save to Original Config", key="save_multi"):
                                        if multi_status != "No change":
                                            status_value = None if multi_status == "None (remove status)" else multi_status
                                            if parser.set_multiple_children_status(indices, status_value):
                                                st.success(f"Status updated to: {status_value or 'None'} for all selected objects")
                                                save_and_download_config(parser, st.session_state.filename)
                                            else:
                                                st.error("Failed to update status for some or all objects")
                                        else:
                                            st.info("No changes to save")
                            else:
                                st.info("Please select at least one object to continue")
                        else:
                            st.info(f"No other objects of class {current_class} found.")
                
                # Children Manager tab
                with operation_tabs[2]:
                    parent_obj = children[index]
                    parent_name = parent_obj['attributes'].get('name', f'Object {index}')
                    parent_class = parent_obj['class']
                    parent_children_count = len(parent_obj.get('children', []))
                    
                    st.subheader(f"Children of {parent_class} - {parent_name}")
                    
                    if parent_children_count == 0:
                        st.info(f"This object has no children.")
                    else:
                        st.write(f"Managing {parent_children_count} children objects")
                        
                        # Get children of the selected parent
                        child_children = parser.get_child_children(index)
                        
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
                                        'Description': child_attributes.get('descr', ''),
                                        'Status': child_attributes.get('status', 'N/A'),
                                        'Children': child_children_count
                                    })
                            
                            # Create dataframe and apply filtering for children
                            child_df = pd.DataFrame(child_records)
                            
                            # Filter and sort options for children
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                child_class_filter = st.multiselect(
                                    "Filter children by class:",
                                    options=sorted(child_df['Class'].unique()) if not child_df.empty else [],
                                    key="child_class_filter"
                                )
                            
                            with col2:
                                child_name_filter = st.text_input(
                                    "Filter children by name:",
                                    key="child_name_filter_input"
                                )
                                
                            with col3:
                                child_sort_by = st.selectbox(
                                    "Sort children by:",
                                    options=["Index", "Class", "Name", "Status", "Children (desc)"],
                                    index=0,
                                    key="child_sort_by"
                                )
                            
                            # Apply filters to child dataframe
                            filtered_child_df = child_df
                            if child_class_filter:
                                filtered_child_df = filtered_child_df[filtered_child_df['Class'].isin(child_class_filter)]
                            if child_name_filter:
                                filtered_child_df = filtered_child_df[filtered_child_df['Name'].str.contains(child_name_filter, case=False, na=False)]
                                
                            # Apply sorting to children
                            if child_sort_by == "Index":
                                filtered_child_df = filtered_child_df.sort_values('Index')
                            elif child_sort_by == "Class":
                                filtered_child_df = filtered_child_df.sort_values('Class')
                            elif child_sort_by == "Name":
                                filtered_child_df = filtered_child_df.sort_values('Name')
                            elif child_sort_by == "Status":
                                filtered_child_df = filtered_child_df.sort_values('Status')
                            elif child_sort_by == "Children (desc)":
                                filtered_child_df = filtered_child_df.sort_values('Children', ascending=False)
                            
                            # Display filtered children table
                            if not filtered_child_df.empty:
                                st.dataframe(filtered_child_df, use_container_width=True)
                                
                                # Create selection options for children
                                child_options = []
                                for _, row in filtered_child_df.iterrows():
                                    idx = row['Index']
                                    name = row['Name']
                                    child_class = row['Class']
                                    status = row['Status']
                                    child_children = row['Children']
                                    child_options.append(f"{idx}: {child_class} - {name} | Status: {status} | Children: {child_children}")
                                
                                # Status modification and actions for filtered children
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    multi_child_status = st.selectbox(
                                        "Set status for filtered children:",
                                        options=STATUS_OPTIONS,
                                        key="filtered_child_status"
                                    )
                                
                                with col2:
                                    multi_child_filename = st.text_input(
                                        "Output filename:", 
                                        f"filtered_children_of_{parent_class}_{index}.json",
                                        key="filtered_child_filename"
                                    )
                                
                                # Get indices of filtered children
                                child_indices = filtered_child_df['Index'].tolist()
                                
                                # Preview the filtered children
                                with st.expander(f"Preview ({len(child_indices)} children filtered)", expanded=True):
                                    combined_child_config = parser.get_multiple_child_children_config(index, child_indices)
                                    if combined_child_config:
                                        st.json(combined_child_config)
                                
                                # Action buttons for filtered children
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button("Extract Filtered Children", key="extract_filtered_children"):
                                        # First update status if requested
                                        if multi_child_status != "No change":
                                            status_value = None if multi_child_status == "None (remove status)" else multi_child_status
                                            success = parser.set_multiple_child_children_status(index, child_indices, status_value)
                                            if success:
                                                st.success(f"Status set to: {status_value or 'None'} for filtered children")
                                            else:
                                                st.warning("Status updates may have been incomplete")
                                        
                                        # Extract children to file
                                        temp_file = os.path.join(tempfile.gettempdir(), multi_child_filename)
                                        success, count = parser.extract_child_children_to_file(index, child_indices, temp_file)
                                        
                                        if success:
                                            with open(temp_file, 'r') as f:
                                                children_data = json.load(f)
                                            st.success(f"{count} children extracted successfully!")
                                            st.markdown(
                                                create_download_link(children_data, multi_child_filename, "Download JSON file"),
                                                unsafe_allow_html=True
                                            )
                                        else:
                                            st.error("Failed to extract children")
                                
                                with col2:
                                    if st.button("Update Status in Config", key="update_filtered_children_status"):
                                        if multi_child_status != "No change":
                                            status_value = None if multi_child_status == "None (remove status)" else multi_child_status
                                            if parser.set_multiple_child_children_status(index, child_indices, status_value):
                                                st.success(f"Status updated to: {status_value or 'None'} for all filtered children")
                                                save_and_download_config(parser, st.session_state.filename)
                                            else:
                                                st.error("Failed to update some or all children statuses")
                                        else:
                                            st.info("No changes to save")
                            else:
                                st.info("No children match the current filters. Please adjust your filter criteria.")
    else:
        st.warning("No child objects found in the configuration.")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("APIC Parser - Web Interface")