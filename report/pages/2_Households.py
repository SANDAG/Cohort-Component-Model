import streamlit as st
import pandas as pd
import plotly.express as px
import utils

# Households
# Load household output and summarize by year
households = (
    st.session_state.population_data
    .groupby("year")[
        [
            "pop",
            "gq",
            "hh",
            "hh_head_lf",
            "child1",
            "senior1",
            "size1",
            "size2",
            "size3",
            "workers0",
            "workers1",
            "workers2",
            "workers3",
        ]
    ]
    .sum()
    .reset_index()
    .assign(
        pph=lambda x: (x["pop"] - x["gq"]) / x["hh"],
        hh_head_lf=lambda x: 100 * x["hh_head_lf"] / x["hh"],
        child1=lambda x: 100 * x["child1"] / x["hh"],
        senior1=lambda x: 100 * x["senior1"] / x["hh"],
        size1=lambda x: 100 * x["size1"] / x["hh"],
        size2=lambda x: 100 * x["size2"] / x["hh"],
        size3=lambda x: 100 * x["size3"] / x["hh"],
        workers0=lambda x: 100 * x["workers0"] / x["hh"],
        workers1=lambda x: 100 * x["workers1"] / x["hh"],
        workers2=lambda x: 100 * x["workers2"] / x["hh"],
        workers3=lambda x: 100 * x["workers3"] / x["hh"],
    )
    .rename(
        columns={
            "year": "Year",
            "hh": "Total Households",
            "pph": "Persons per Household",
            "hh_head_lf": "Households with Head in Labor Force",
            "child1": "Households with Children",
            "senior1": "Households with Seniors",
            "size1": "Households with 1 Person",
            "size2": "Households with 2 Persons",
            "size3": "Households with 3+ Persons",
            "workers0": "Households with 0 Workers",
            "workers1": "Households with 1 Worker",
            "workers2": "Households with 2 Workers",
            "workers3": "Households with 3+ Workers",
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
    .drop(columns=["Year", "pop", "gq"])
    .melt(var_name="Category", value_name="Value")
    .assign(Metric=lambda x: x["Category"].apply(utils.hh_metrics))
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