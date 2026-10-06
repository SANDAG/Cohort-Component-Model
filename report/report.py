import streamlit as st

# Set up navigation for the report pages
pg = st.navigation(
    [
        st.Page("pages/Home.py", title="Home", default=True),
        st.Page("pages/Population.py", title="Population"),
        st.Page("pages/Households.py", title="Households"),
        st.Page("pages/Rates.py", title="Rates"),
    ]
)
pg.run()
