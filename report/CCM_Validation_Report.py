import os
import utils
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

# Definitions for getting data from SQL
def get_run_metadata(_sql_engine: sql.engine) -> pd.DataFrame:
    with _sql_engine.connect() as connection:
        with open("./report/metadata.sql", "r") as query:
            return pd.read_sql_query(
                sql.text(query.read()),
                connection,
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
# crate variables for file paths of csv files
population_file = "output/population.csv"
components_file = "output/components.csv"
rates_file = "output/rates.csv"

if data_selector == "CSV":
    # Check if CSV(S) exist. If not write user error message. If all exist write user message and read in csv files
    if os.path.exists(population_file) and os.path.exists(components_file) and os.path.exists(rates_file):
        # Load in CSVs from output folder       
        pop = utils.get_data(data_selector = data_selector, file_path = population_file)
        comp = utils.get_data(data_selector = data_selector, file_path = components_file)
        rates = utils.get_data(data_selector = data_selector, file_path = rates_file)
        
        # Save datasets from CSVs. Display error message if problem loading data
        if True in pop:
            st.session_state.population_data = pop[True]
        else:
            st.error(pop[False])
        
        if True in comp:
                st.session_state.components_data = comp[True]
        else:
            st.error(comp[False])

        if True in rates:
            st.session_state.rates_data = rates[True]
        else:
            st.error(rates[False])

        # Put messsage saying CSVs loaded successfully, select report from left side menu
        if True in pop and True in comp and True in rates:
            st.success("✅ All CSVs Loaded. Select Report From Left Side Menu")
    else: 
        st.error(f"❌ Missing CSV Output(s), Check All Outputs Exists")


# Add in section for what to do if "SQL Database" optionn selected
elif data_selector == "SQL Database":
    # SQL scripts to be used to pull data from database
    pop_script = "./report/population.sql"
    comp_script = "./report/components.sql"
    rates_script = "./report/rates.sql"


    # Build SQL engine from secrets file
    with open("./secrets.yml", "r") as file:
        secrets = yaml.safe_load(file)

    engine = sql.create_engine(
        "mssql+pymssql://" + secrets["sql"]["server"] + "/" + secrets["sql"]["database"]
    )

    # Tables to check: list of (schema, table_name) tuples 
    tables_to_check = [
        ("metadata", "run"),
        ("outputs", "population"),
        ("outputs", "components"),
        ("outputs", "rates"),        
    ]

    # Function to check table existence 
    def sql_table_exists(schema, table_name):
        query = """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
        """
        with engine.connect() as conn:
            result = conn.execute(sql.text(query), {"schema": schema, "table": table_name}).fetchone()
        return result is not None
    
    # Check all tables 
    missing_tables = []
    for schema, table in tables_to_check:
        if not sql_table_exists(schema, table):
            missing_tables.append(f"{schema}.{table}")
    # What to do if all tables exists
    if not missing_tables:
        
        # Load run metadata
        run_df = get_run_metadata(_sql_engine=engine)

        # Allow user to select a single run from the metadata table
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

            pop = utils.get_data(data_selector = data_selector, run_id = st.session_state.run_id, engine = engine, sql_script = pop_script)
            comp = utils.get_data(data_selector = data_selector, run_id = st.session_state.run_id, engine = engine, sql_script = comp_script)
            rates = utils.get_data(data_selector = data_selector, run_id = st.session_state.run_id, engine = engine, sql_script = rates_script)

            # Save datasets from SQL Database with run_id. Display error message if problem loading data
            if True in pop:
                st.session_state.population_data = pop[True]
            else:
                st.error(pop[False])
            
            if True in comp:
                st.session_state.components_data = comp[True]
            else:
                st.error(comp[False])

            if True in rates:
                st.session_state.rates_data = rates[True]
            else:
                st.error(rates[False])

            # Put messsage saying output loaded successfully, select report from left side menu
            if True in pop and True in comp and True in rates:
                st.success("✅ All Output Loaded. Select Report From Left Side Menu")

    # Add in Message to user if SQL table(s) dont't exist    
    else:
        st.error(f"❌ Missing tables: {', '.join(missing_tables)}")

# Do nothing if no datasource selected
else: 
    pass





