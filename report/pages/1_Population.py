import streamlit as st
import pandas as pd
import plotly.express as px
import report_utils
import plotly.graph_objs as go
import numpy as np

# Population
# Sub-tabs for population, components of change, and demographics
tab1, tab2, tab3 = st.tabs(["Total", "Components", "Demographics"])

# Total Population
with tab1:
    # Load total population output and summarize by year
    total = (
        st.session_state.population_data
        .groupby("year")[["pop", "pop_mil", "gq"]]
        .sum()
        .reset_index()
        .assign(pop_hh=lambda x: x["pop"] - x["gq"])
        .rename(
            columns={
                "year": "Year",
                "pop": "Total Population",
                "pop_hh": "Household Population",
                "gq": "Group Quarters",
                "pop_mil": "Military Population",
            }
        )
    )

    # Show total population in a line chart
    fig = px.line(
        total,
        x="Year",
        y="Total Population",
        title="San Diego Region: Total Population",
        labels={"Year": "", "Total Population": ""},
        line_shape="spline",
    )

    st.plotly_chart(fig)

    # Show detailed total population in a table
    st.dataframe(
        total,
        hide_index=True,
        column_order=[
            "Year",
            "Total Population",
            "Household Population",
            "Group Quarters",
            "Military Population",
        ],
        column_config={
            k: st.column_config.NumberColumn(format="localized")
            for k in [
                "Total Population",
                "Household Population",
                "Group Quarters",
                "Military Population",
            ]
        },
    )

# Components of Change
with tab2:
    # Load components of change output and summarize by year
    components = (
        st.session_state.components_data
        .groupby("year")[["births", "deaths", "ins", "outs"]]
        .sum()
        .reset_index()
        .assign(
            net=lambda x: x["ins"] - x["outs"],
            natural=lambda x: x["births"] - x["deaths"],
            total=lambda x: x["net"] + x["natural"],
        )
        .rename(
            columns={
                "year": "Year",
                "total": "Total Change",
                "natural": "Natural Change",
                "births": "Births",
                "deaths": "Deaths",
                "net": "Net Migration",
                "ins": "In-Migration",
                "outs": "Out-Migration",
            }
        )
    )

    # Show summarized components of change in a line chart
    fig = px.line(
        components,
        x="Year",
        y=["Natural Change", "Net Migration"],
        title="San Diego Region: Components of Population Change",
        labels={"Year": "", "value": ""},
        line_shape="spline",
    )

    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig)

    # Show detailed components of change in a table
    st.dataframe(
        components,
        hide_index=True,
        column_order=[
            "Year",
            "Total Change",
            "Natural Change",
            "Births",
            "Deaths",
            "Net Migration",
            "In-Migration",
            "Out-Migration",
        ],
        column_config={
            k: st.column_config.NumberColumn(format="localized")
            for k in [
                "Total Change",
                "Natural Change",
                "Births",
                "Deaths",
                "Net Migration",
                "In-Migration",
                "Out-Migration",
            ]
        },
    )

# Demographics
with tab3:
    # Load population pyramid output and summarize by year
    pyramid = (
        st.session_state.population_data
        .assign(age_grp=lambda x: x["age"].apply(report_utils.age_5y))
        .groupby(["year", "sex", "age_grp"])["pop"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "year": "Year",
                "sex": "Sex",
                "age_grp": "Age",
                "pop": "Total Population",
            }
        )
    )

    # Create year slider and filter dataset
    tab3_year = st.slider(
        label="**Forecast Year:**",
        min_value=pyramid["Year"].min(),
        max_value=pyramid["Year"].max(),
        key="tab3_year",
    )

    pyramid_year = pyramid[pyramid["Year"] == tab3_year]

    # Create population pyramid chart
    layout = go.Layout(
        title="San Diego Region: Demographics",
        xaxis=go.layout.XAxis(
            range=[
                abs(pyramid["Total Population"]).max() * -1,
                abs(pyramid["Total Population"]).max(),
            ],
            title="Population",
        ),
        barmode="overlay",
    )

    data = []
    for sex in ["M", "F"]:
        sex_data = pyramid_year[pyramid_year["Sex"] == sex]
        values = sex_data["Total Population"].values

        if sex == "F":
            name = "Female"
            values = [-i for i in values]
        else:
            name = "Male"

        data.append(
            go.Bar(
                y=list(report_utils.MAP_5Y_AGE_GROUPS.keys()),
                x=values,
                orientation="h",
                name=name,
            )
        )

    fig = go.Figure(data=data, layout=layout)
    st.plotly_chart(fig)

    # Create and show detailed demographic data in a table
    demographics = st.session_state.population_data.query("year == @tab3_year")

    tbl = []
    for field in ["age", "sex", "race"]:
        if field != "age":
            df = (
                demographics.rename(columns={field: "Category"})
                .groupby("Category")["pop"]
                .sum()
                .reset_index()
                .assign(
                    Metric="Pct of Total - " + field,
                    Value=lambda x: 100 * x["pop"] / x["pop"].sum(),
                )
                .drop(columns=["pop"])
            )

            if field == "sex":
                df["Category"] = df["Category"].map({"F": "Female", "M": "Male"})
        else:
            ages = np.repeat(demographics["age"], demographics["pop"])
            df = pd.DataFrame(
                {
                    "Category": "Age",
                    "Metric": "Median Age",
                    "Value": np.median(ages),
                },
                index=[0],
            )

        tbl.append(df)

    st.dataframe(
        pd.concat(tbl, ignore_index=True),
        hide_index=True,
        column_order=[
            "Metric",
            "Category",
            "Value",
        ],
        column_config={"Value": st.column_config.NumberColumn(format="localized")},
    )