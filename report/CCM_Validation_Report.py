import os
import report_utils
import yaml

import pandas as pd
import streamlit as st
import sqlalchemy as sql

from typing import Union

st.set_page_config(
    page_title="CCM Validation Report"
)

# Create Title for landing page
st.write("# CCM Validation Reporting Tool")

# This Creates note below selection list on left hand side of page
st.sidebar.success("Select a report above.") 

# This is bulk of text on the landing page
st.markdown(
    """
    This is a streamlit report to review and check the outputs of
    the Cohort Component Model (CCM). **Select an output to review 
    from the sidebar**. The Cohort Component Model is a demographic 
    modeling system used to project the population and households 
    of the region. The Cohort Component Method is used to developed 
    SANDAG's Regional Forecast using assumptions regarding fertility, 
    mortality, migration and headship rates that align with the 
    future economy of the San Diego Metropolitan Area.
"""
)

# Set session state variables To None before a selection of Dataset
for key in ["population_data", "components_data", "rates_data"]:
    if key not in st.session_state:
        st.session_state[key] = None
    else:
        del st.session_state[key]

# Add in message about selecting data source for report generation
st.markdown("#### Select which data source you want to use for report generation")
# Create radio buttons for selectiong the data source to be used in report generation
data_selector = st.radio(
    "",
    ["CSV", "SQL Database"],
    index = None,
    label_visibility = "collapsed"
)

# CSV section for what to do if "CSV" option selected
if data_selector == "CSV":
    # Check if CSV(S) exist. If not write user error message. If all exist write user message and read in csv files
    # Try to load in CSVs
    csv_dict = report_utils.get_data(data_selector = data_selector, run_id = None)
    if True in csv_dict["population"] and True in csv_dict["components"] and True in csv_dict["rates"]:
        st.session_state.population_data = csv_dict["population"][True]
        st.session_state.components_data = csv_dict["components"][True]
        st.session_state.rates_data = csv_dict["rates"][True]
        # Put messsage saying CSVs loaded successfully, select report from left side menu
        st.success("✅ All CSVs Loaded. Select Report From Left Side Menu")
    
    else:
        failed = [
            name for name in ["population", "components", "rates"]
            if True not in csv_dict[name]
        ]
        failed_str = ", ".join(failed)
        st.error(f"❌ Missing or unreadable CSV Output(s): [{failed_str}]")

# Add in section for what to do if "SQL Database" optionn selected
elif data_selector == "SQL Database":
    
    # NEED TO LOAD METADATA FIRST AND SELECT A RUN ID
    metadata = report_utils.get_metadata()
    if True in metadata:

        run_df = metadata[True]

        runs = st.dataframe(
            data=run_df[["run_id", "user", "date", "version", "comments", "launch", "horizon"]],
            hide_index=True,
            column_config={"year": st.column_config.TextColumn("year", max_chars=4)},
            on_select="rerun",
            selection_mode="single-row",
        )

        # What to do if no run_id is selected
        if not runs["selection"]["rows"]:
            # Set session state variables for data to None if haven't selected run
            for key in ["population_dat","components_data", "rates_data"]:
                if key not in st.session_state:
                    st.session_state[key] = None
                else:
                    del st.session_state[key]
            # Display message to user under selection table telling them to select run_id
            st.error(f"Select run_id")
        
        # What to do once run_id is selected
        else:

            # Get run_id from user selection and persist selected run_id in session state
            idx = runs["selection"]["rows"][0]
            st.session_state.run_id = run_df.iloc[idx]["run_id"]
            
            # Try to load in SQL Data
            sql_dict = report_utils.get_data(data_selector = data_selector, run_id = st.session_state.run_id)
            
            # Logic if no tables missing
            if True in sql_dict["population"] and True in sql_dict["components"] and True in sql_dict["rates"]:

                    st.session_state.population_data = sql_dict["population"][True]
                    st.session_state.components_data = sql_dict["components"][True]
                    st.session_state.rates_data = sql_dict["rates"][True]
                    # Put messsage saying CSVs loaded successfully, select report from left side menu
                    st.success("✅ All CSVs Loaded. Select Report From Left Side Menu")
            
            else:
                failed = [
                    name for name in ["population", "components", "rates"]
                    if True not in sql_dict[name]
                ]
                failed_str = ", ".join(failed)
                st.error(f"❌ Missing or unreadable SQL Output(s): [{failed_str}]")

    else: 
        # Write message if can't load Metadata Table
        st.error(f"❌ Missing or unreadable Metadata table")

# Do nothing if no datasource selected
else: 
    pass





