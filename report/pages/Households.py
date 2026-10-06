import report_utils

import streamlit as st

import plotly.express as px

# Households
# Load household output and summarize by year
households = (
    st.session_state.population_data.groupby("year")[
        [
            "pop",
            "gq_mil",
            "gq_prison",
            "gq_college",
            "gq_other",
            "hh",
            "hh_size1",
            "hh_size2",
            "hh_size3",
            "hh_workers0",
            "hh_workers1",
            "hh_workers2",
            "hh_workers3",
            "hh_head_lf",
            "hh_children",
            "hh_seniors",
        ]
    ]
    .sum()
    .reset_index()
    .assign(
        pph=lambda x: (
            x["pop"] - x["gq_college"] - x["gq_prison"] - x["gq_mil"] - x["gq_other"]
        )
        / x["hh"],
        hh_head_lf=lambda x: 100 * x["hh_head_lf"] / x["hh"],
        hh_children=lambda x: 100 * x["hh_children"] / x["hh"],
        hh_seniors=lambda x: 100 * x["hh_seniors"] / x["hh"],
        hh_size1=lambda x: 100 * x["hh_size1"] / x["hh"],
        hh_size2=lambda x: 100 * x["hh_size2"] / x["hh"],
        hh_size3=lambda x: 100 * x["hh_size3"] / x["hh"],
        hh_workers0=lambda x: 100 * x["hh_workers0"] / x["hh"],
        hh_workers1=lambda x: 100 * x["hh_workers1"] / x["hh"],
        hh_workers2=lambda x: 100 * x["hh_workers2"] / x["hh"],
        hh_workers3=lambda x: 100 * x["hh_workers3"] / x["hh"],
    )
    .rename(
        columns={
            "year": "Year",
            "hh": "Total Households",
            "pph": "Persons per Household",
            "hh_head_lf": "Households with Head in Labor Force",
            "hh_children": "Households with Children",
            "hh_seniors": "Households with Seniors",
            "hh_size1": "Households with 1 Person",
            "hh_size2": "Households with 2 Persons",
            "hh_size3": "Households with 3+ Persons",
            "hh_workers0": "Households with 0 Workers",
            "hh_workers1": "Households with 1 Worker",
            "hh_workers2": "Households with 2 Workers",
            "hh_workers3": "Households with 3+ Workers",
        }
    )
)

# Show total households in a line chart
fig = px.line(
    households,
    x="Year",
    y="Total Households",
    title="San Diego Region: Total Households",
    labels={"Year": "", "Total Households": ""},
)

st.plotly_chart(fig)

# Show detailed household data in a table
# Create year slider to filter dataset
year = st.slider(
    label="**Forecast Year:**",
    min_value=households["Year"].min(),
    max_value=households["Year"].max(),
    key="year",
)

# Filter and transform dataset for display
households = (
    (households[households["Year"] == year])
    .drop(columns=["Year", "pop", "gq_college", "gq_prison", "gq_mil", "gq_other"])
    .melt(var_name="Category", value_name="Value")
    .assign(Metric=lambda x: x["Category"].apply(report_utils.hh_metrics))
)

st.dataframe(
    households,
    hide_index=True,
    column_order=[
        "Metric",
        "Category",
        "Value",
    ],
    column_config={"Value": st.column_config.NumberColumn(format="localized")},
)
