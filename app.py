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
    set_object_status
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
    
    # Create and display the table
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

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
        2. View top-level objects
        3. Search for specific objects
        4. Set status (create/delete) if needed
        5. View and download results
        """)
    
    # Main content area - Tabs
    if 'file_processed' in st.session_state and st.session_state.file_processed:
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Search", "ℹ️ About"])
        
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
            
            col1, col2 = st.columns([1, 2])
            with col1:
                object_type = st.text_input("Object Type (e.g., fvBD)", placeholder="fvBD")
            with col2:
                object_names = st.text_input("Object Name(s)", placeholder="BD_484 or BD_484,BD_721", help="For multiple objects, separate with commas")
            
            # Status setting options
            status_col1, status_col2 = st.columns([1, 2])
            with status_col1:
                set_status = st.checkbox("Set Status", help="Set status for found objects")
            with status_col2:
                if set_status:
                    status_type = st.radio(
                        "Status Type", 
                        ["create", "delete"], 
                        horizontal=True,
                        help="'create' sets status to 'created,modified', 'delete' sets status to 'deleted'"
                    )
                else:
                    status_type = None
            
            search_clicked = st.button("🔍 Search", type="primary")
            
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
        
        # Tab 3: About
        with tab3:
            st.header("About APIC Parser")
            st.markdown("""
            **APIC Parser** is a tool for parsing and searching through Cisco ACI APIC (Application Policy Infrastructure Controller) JSON configuration files.
            
            ### Features
            - Parse large APIC JSON configuration files using a streaming parser
            - Extract top-level objects from the tenant configuration
            - Search for specific objects by type and name
            - Search for multiple objects in a single command
            - Set object status (create or delete)
            - Output results in the standard APIC JSON format
            
            ### How It Works
            1. The tool uses `ijson` to parse APIC JSON files in a streaming manner, which allows it to efficiently handle large files
            2. When searching for objects, the tool traverses the parsed data structure using an iterative depth-first search approach
            3. Results are wrapped in the standard APIC format, preserving the tenant structure and attributes
            4. Status can be set to either 'created,modified' or 'deleted' as required by APIC
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
        4. Set status (create/delete) for objects if needed
        
        📌 **Example search types:**
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