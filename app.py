#!/usr/bin/env python3
"""
APIC Parser Streamlit App - A web interface for the APIC Parser tool.

This module provides a Streamlit-based web interface for parsing and searching
Cisco ACI APIC JSON configuration files.

Usage:
    streamlit run app.py
"""

import streamlit as st
import json
import os
import tempfile
import pandas as pd
from apic_parser.apic_parser import (
    build_nested_object,
    get_top_level_objects,
    find_object_by_name_iterative,
    find_all_objects_by_name_iterative,
    format_result_in_apic_standard,
    set_object_status,
    find_ap_and_children_by_name,
    get_nested_epgs_from_ap,
    set_status_for_nested_objects,
    get_ap_and_epg_names
)

# Set page configuration
st.set_page_config(
    page_title="APIC Parser",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define functions for the app
def process_uploaded_file(uploaded_file):
    """Process the uploaded JSON file and return the parsed data"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    try:
        parsed_data = build_nested_object(tmp_file_path)
        os.unlink(tmp_file_path)  # Clean up the temp file
        return parsed_data
    except Exception as e:
        os.unlink(tmp_file_path)  # Clean up the temp file
        st.error(f"Error parsing the uploaded file: {e}")
        return None

def display_top_level_objects_table(data):
    """Display the top-level objects in a table format"""
    top_level = get_top_level_objects(data)
    
    if not top_level:
        st.warning("No top-level objects found in the uploaded file.")
        return
    
    # Prepare data for the table
    table_data = []
    for obj in top_level:
        for key, value in obj.items():
            if key != "children":
                table_data.append({"Object Type": key, "Name": value})
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Display the table with improved formatting
    st.dataframe(
        df,
        column_config={
            "Object Type": st.column_config.TextColumn(
                "Object Type",
                help="Type of APIC object"
            ),
            "Name": st.column_config.TextColumn(
                "Name",
                help="Name of the object"
            ),
        },
        hide_index=True,
        use_container_width=True
    )

def search_objects(data, object_type, object_names, status_type=None):
    """Search for objects by type and names"""
    if not object_type or not object_names:
        st.warning("Please provide both object type and name(s).")
        return None
    
    # Parse object names (handle comma-separated values)
    names_list = [name.strip() for name in object_names.split(',')]
    
    with st.spinner(f"Searching for objects of type '{object_type}'..."):
        if len(names_list) > 1:
            results = find_all_objects_by_name_iterative(data, object_type, names_list)
        else:
            result = find_object_by_name_iterative(data, object_type, names_list[0])
            results = [result] if result else []
        
        # Format results in APIC standard format
        formatted_results = format_result_in_apic_standard(results)
        
        # Apply status if requested
        if status_type and formatted_results and formatted_results["totalCount"] != "0":
            formatted_results = set_object_status(formatted_results, names_list, status_type)
        
    return formatted_results if results else None

def search_ap_with_children(data, ap_name, status_type=None, nested_paths=None):
    """Search for Application Profile with all its nested children"""
    if not ap_name:
        st.warning("Please provide an Application Profile name.")
        return None
    
    with st.spinner(f"Searching for Application Profile '{ap_name}'..."):
        result = find_ap_and_children_by_name(data, ap_name)
        
        # Format results in APIC standard format
        formatted_results = format_result_in_apic_standard(result)
        
        # Apply status to AP and nested objects if requested
        if status_type and formatted_results and formatted_results["totalCount"] != "0":
            if nested_paths:
                formatted_results = set_status_for_nested_objects(formatted_results, nested_paths, status_type)
            else:
                # Just set status on the AP itself
                formatted_results = set_object_status(formatted_results, [ap_name], status_type)
    
    return formatted_results if result else None

def get_available_object_types(data):
    """Get a list of all available object types from the data"""
    top_level = get_top_level_objects(data)
    object_types = []
    
    for obj in top_level:
        for key in obj.keys():
            if key != "children" and key not in object_types:
                object_types.append(key)
    
    return sorted(object_types)

def get_object_names_by_type(data, object_type):
    """Get all object names of a specific type"""
    top_level = get_top_level_objects(data)
    names = []
    
    for obj in top_level:
        for key, value in obj.items():
            if key == object_type and value is not None:
                names.append(value)
    
    return sorted(names)

# Main app structure
def main():
    # Header with icon
    st.title("🌐 APIC Parser")
    st.markdown("### A tool for parsing and searching Cisco ACI APIC JSON configuration files")
    
    # Sidebar for file upload
    with st.sidebar:
        st.header("📁 Upload Configuration")
        uploaded_file = st.file_uploader("Choose an APIC JSON file", type=['json'])
        
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            st.session_state.uploaded_file_name = uploaded_file.name
            
            # Process uploaded file
            with st.spinner("Processing file..."):
                parsed_data = process_uploaded_file(uploaded_file)
                if parsed_data:
                    st.session_state.parsed_data = parsed_data
                    st.session_state.file_processed = True
        
        # Display information
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Upload an APIC JSON file
        2. View top-level objects in the Overview tab
        3. Use the Search tab to find and modify objects
        4. Use the Application Profiles tab for nested objects
        5. Set status (create/delete) for objects at any level
        6. View and download results
        """)
    
    # Main content area - Tabs
    if 'file_processed' in st.session_state and st.session_state.file_processed:
        # Use session state to control active tab
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Search", "🌳 Application Profiles", "ℹ️ About"])
        
        # Tab 1: Overview
        with tab1:
            st.header(f"Configuration Overview: {st.session_state.uploaded_file_name}")
            st.subheader("Top-Level Objects")
            display_top_level_objects_table(st.session_state.parsed_data)
            
            # Option to view JSON structure
            if st.checkbox("Show Raw JSON Structure"):
                st.json(st.session_state.parsed_data)
        
        # Tab 2: Search
        with tab2:
            st.header("Search for Objects")
            
            # Get available object types for dropdown
            object_types = [""] + get_available_object_types(st.session_state.parsed_data)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Use dropdown with available types
                object_type = st.selectbox(
                    "Object Type",
                    options=object_types,
                    index=0
                )
            
            with col2:
                # If an object type is selected, get names for that type and show as a multiselect
                if object_type:
                    object_names_list = get_object_names_by_type(st.session_state.parsed_data, object_type)
                    selected_names = st.multiselect(
                        "Select Object Name(s)",
                        options=object_names_list,
                        help="You can select multiple objects of the same type"
                    )
                    
                    # Convert selected names to comma-separated string for the search function
                    object_names = ",".join(selected_names) if selected_names else ""
                else:
                    object_names = ""
                    st.text("Please select an Object Type first")
            
            # Status setting options
            status_col1, status_col2 = st.columns([1, 2])
            with status_col1:
                set_status = st.checkbox("Set Status", help="Set status for found objects", key="search_set_status")
            with status_col2:
                if set_status:
                    status_type = st.radio(
                        "Status Type", 
                        ["create", "delete"], 
                        horizontal=True,
                        help="'create' sets status to 'created,modified', 'delete' sets status to 'deleted'",
                        key="search_status_type"
                    )
                else:
                    status_type = None
            
            search_clicked = st.button("🔍 Search", type="primary", disabled=not (object_type and object_names))
            
            if search_clicked and object_type and object_names:
                results = search_objects(st.session_state.parsed_data, object_type, object_names, status_type if set_status else None)
                if results:
                    st.session_state.search_results = results
                    st.success(f"Found {results['totalCount']} object(s)")
                    
                    if set_status:
                        status_value = "deleted" if status_type == "delete" else "created,modified"
                        st.info(f"Status set to '{status_value}' for the found object(s)")
                    
                    # Show results
                    with st.expander("View Results", expanded=True):
                        st.json(results)
                    
                    # Download button for results
                    result_json = json.dumps(results, indent=2)
                    st.download_button(
                        label="📥 Download Results",
                        data=result_json,
                        file_name="apic_search_results.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"No objects found matching the criteria.")
        
        # Tab 3: Application Profiles
        with tab3:
            st.header("Browse Application Profiles and EPGs")
            st.info("This tab helps you work with nested objects like Application Profiles (fvAp) and their EPGs (fvAEPg)")
            
            # Get all Application Profiles and their EPGs
            with st.spinner("Loading Application Profiles and EPGs..."):
                ap_epg_dict = get_ap_and_epg_names(st.session_state.parsed_data)
            
            if not ap_epg_dict:
                st.warning("No Application Profiles found in the configuration.")
            else:
                # Show Application Profiles in a dropdown
                ap_names = list(ap_epg_dict.keys())
                selected_ap = st.selectbox("Select Application Profile", options=[""] + ap_names)
                
                if selected_ap:
                    # Show EPGs for the selected AP
                    st.subheader(f"EPGs in {selected_ap}")
                    epgs = ap_epg_dict[selected_ap]
                    
                    if not epgs:
                        st.info(f"No EPGs found in Application Profile '{selected_ap}'")
                    else:
                        # Display EPGs in a table
                        epg_df = pd.DataFrame({"EPG Name": epgs})
                        st.dataframe(
                            epg_df,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Allow selection of EPGs
                        selected_epgs = st.multiselect(
                            "Select EPGs to include in status update", 
                            options=epgs
                        )
                        
                        # Status setting options for nested objects
                        st.subheader("Set Status for Objects")
                        
                        status_options = st.columns(3)
                        with status_options[0]:
                            set_ap_status = st.checkbox("Set AP Status", help="Set status for the Application Profile", key="ap_set_status")
                        
                        with status_options[1]:
                            set_epg_status = st.checkbox("Set EPG Status", help="Set status for selected EPGs", key="epg_set_status")
                            
                        with status_options[2]:
                            status_type = st.radio(
                                "Status Type", 
                                ["create", "delete"], 
                                horizontal=True,
                                help="'create' sets status to 'created,modified', 'delete' sets status to 'deleted'",
                                key="ap_status_type"
                            )
                        
                        # Button to retrieve AP with status updates
                        retrieve_button = st.button(
                            "📋 Retrieve with Status Updates", 
                            type="primary",
                            disabled=not (selected_ap and (set_ap_status or (set_epg_status and selected_epgs)))
                        )
                        
                        if retrieve_button:
                            # Build paths for status updates
                            object_paths = []
                            
                            if set_ap_status:
                                object_paths.append(f"fvAp:{selected_ap}")
                                
                            if set_epg_status and selected_epgs:
                                for epg in selected_epgs:
                                    object_paths.append(f"fvAp:{selected_ap}/fvAEPg:{epg}")
                            
                            # Retrieve AP with nested children and set status
                            with st.spinner(f"Retrieving Application Profile '{selected_ap}' and updating status..."):
                                results = search_ap_with_children(
                                    st.session_state.parsed_data,
                                    selected_ap,
                                    status_type=status_type if (set_ap_status or set_epg_status) else None,
                                    nested_paths=object_paths
                                )
                                
                                if results:
                                    # Show what objects had status set
                                    if set_ap_status or set_epg_status:
                                        status_value = "deleted" if status_type == "delete" else "created,modified"
                                        objects_updated = []
                                        
                                        if set_ap_status:
                                            objects_updated.append(f"Application Profile '{selected_ap}'")
                                            
                                        if set_epg_status and selected_epgs:
                                            for epg in selected_epgs:
                                                objects_updated.append(f"EPG '{epg}'")
                                        
                                        st.success(f"Status set to '{status_value}' for {len(objects_updated)} object(s)")
                                        st.write("Updated objects:")
                                        for obj in objects_updated:
                                            st.write(f"- {obj}")
                                    
                                    # Show results
                                    with st.expander("View Results", expanded=True):
                                        st.json(results)
                                    
                                    # Download button for results
                                    result_json = json.dumps(results, indent=2)
                                    st.download_button(
                                        label="📥 Download Results",
                                        data=result_json,
                                        file_name=f"ap_{selected_ap}_with_status.json",
                                        mime="application/json"
                                    )
                                else:
                                    st.error(f"Failed to retrieve Application Profile '{selected_ap}'")
        
        # Tab 4: About
        with tab4:
            st.header("About APIC Parser")
            st.markdown("""
            **APIC Parser** is a tool for parsing and searching through Cisco ACI APIC (Application Policy Infrastructure Controller) JSON configuration files.
            
            ### Features
            - Parse large APIC JSON configuration files using a streaming parser
            - Extract top-level objects from the tenant configuration
            - Search for specific objects by type and name
            - Search for multiple objects in a single command
            - Browse and modify Application Profiles with nested EPGs
            - Set status attributes for objects at any level in the hierarchy
            - Output results in the standard APIC JSON format
            
            ### How It Works
            1. The tool uses `ijson` to parse APIC JSON files in a streaming manner, which allows it to efficiently handle large files
            2. When searching for objects, the tool traverses the parsed data structure using an iterative depth-first search approach
            3. Results are wrapped in the standard APIC format, preserving the tenant structure and attributes
            4. Status can be set to either 'created,modified' or 'deleted' as required by APIC
            5. Hierarchical object relationships are preserved when browsing Application Profiles and EPGs
            """)
    else:
        # Display welcome message when no file is uploaded yet
        st.header("Welcome to APIC Parser")
        st.markdown("""
        This tool helps you explore and search through Cisco ACI APIC JSON configuration files.
        
        To get started:
        1. Upload an APIC JSON file using the sidebar
        2. The app will automatically parse the file
        3. You can then explore the structure and search for specific objects
        4. Browse Application Profiles and their nested EPGs
        5. Set status (create/delete) for objects at any level
        
        📌 **Example object types:**
        - Bridge Domains: `fvBD`
        - Application Profiles: `fvAp`
        - EPGs: `fvAEPg`
        - Contracts: `vzBrCP`
        - Filters: `vzFilter`
        """)
        
        # Display a card with information
        st.info("📢 This app processes files locally and does not upload your data to any external server.")

# Run the app
if __name__ == "__main__":
    main()