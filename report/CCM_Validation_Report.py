import streamlit as st

st.set_page_config(
    page_title="CCM Validation Report"
)

#Create Title for landing page
st.write("# CCM Validation Reporting Tool")

#This Creates note below selection list on left hand side of page
st.sidebar.success("Select a report above.") 

#This is bulk of text on the landing page
st.markdown(
    """
    This is a streamlit report to review and check the outputs of
    the Cohorth Component Model (CCM). **Select a output to review 
    from the sidebar** The Cohort Component Model is a demographic 
    modeling system used to project the population and households 
    of the region. The Cohort Component Method is used to developed 
    SANDAG's Regional Forecast using assumptions regarding fertility, 
    mortality, migration and headship rates that align with the 
    future economy of the San Diego Metropolitan Area.
    ### The CCM Model Creates Three Outputs Each with a Validation Report
    - Population
    - Households
    - Rates
"""
)