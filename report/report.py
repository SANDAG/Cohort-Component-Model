import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import streamlit as st
import utils


# Enumerate and label tabs in report
tab1, tab2, tab3 = st.tabs(["Population", "Households", "Rates"])

# Population
with tab1:
    # Sub-tabs for population, components of change, and demographics
    tab1_1, tab1_2, tab1_3 = st.tabs(["Total", "Components", "Demographics"])

    # Total Population
    with tab1_1:
        # Load total population output and summarize by year
        total = (
            pd.read_csv("output/population.csv")
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
                "Total Population": st.column_config.NumberColumn(format="localized"),
                "Household Population": st.column_config.NumberColumn(
                    format="localized"
                ),
                "Group Quarters": st.column_config.NumberColumn(format="localized"),
                "Military Population": st.column_config.NumberColumn(
                    format="localized"
                ),
            },
        )

    # Components of Change
    with tab1_2:
        # Load components of change output and summarize by year
        components = (
            pd.read_csv("output/components.csv")
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
                "Total Change": st.column_config.NumberColumn(format="localized"),
                "Natural Change": st.column_config.NumberColumn(format="localized"),
                "Births": st.column_config.NumberColumn(format="localized"),
                "Deaths": st.column_config.NumberColumn(format="localized"),
                "Net Migration": st.column_config.NumberColumn(format="localized"),
                "In-Migration": st.column_config.NumberColumn(format="localized"),
                "Out-Migration": st.column_config.NumberColumn(format="localized"),
            },
        )

    # Demographics
    with tab1_3:
        # Load population pyramid output and summarize by year
        pyramid = (
            pd.read_csv("output/population.csv")
            .assign(age_grp=lambda x: x["age"].apply(utils.age_5y))
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
        tab1_3_year = st.slider(
            label="**Forecast Year:**",
            min_value=pyramid["Year"].min(),
            max_value=pyramid["Year"].max(),
            key="tab1_3_year",
        )

        pyramid_year = pyramid[pyramid["Year"] == tab1_3_year]

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
                    y=list(utils.MAP_5Y_AGE_GROUPS.keys()),
                    x=values,
                    orientation="h",
                    name=name,
                )
            )

        fig = go.Figure(data=data, layout=layout)
        st.plotly_chart(fig)

        # Create and show detailed demographic data in a table
        demographics = pd.read_csv("output/population.csv").query(
            "year == @tab1_3_year"
        )

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

# Households
with tab2:
    # Load household output and summarize by year
    households = (
        pd.read_csv("output/population.csv")
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
    tab2_year = st.slider(
        label="**Forecast Year:**",
        min_value=households["Year"].min(),
        max_value=households["Year"].max(),
        key="tab2_year",
    )

    # Filter and transform dataset for display
    households = (
        (households[households["Year"] == tab2_year])
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

# Rates
with tab3:
    # Sub-tabs for fertility, mortality, and migration rates
    tab3_1, tab3_2, tab3_3 = st.tabs(["Fertility", "Mortality", "Migration"])

    # Fertility Rates
    with tab3_1:
        # Load fertility rate data
        fertility = (
            pd.read_csv("output/rates.csv")[
                ["year", "race", "sex", "age", "rate_birth"]
            ]
            .query("age >= 15 & age <= 45")
            .rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})
        )

        # Create year slider and filter dataset
        tab3_1_year = st.slider(
            label="**Forecast Year:**",
            min_value=fertility["Year"].min(),
            max_value=fertility["Year"].max(),
            key="tab3_1_year",
        )

        fertility = fertility.query("Year == @tab3_1_year")

        # Show fertility rates in a line chart
        fig = px.line(
            fertility,
            x="Age",
            y="rate_birth",
            range_x=[15, 45],
            range_y=[0, fertility["rate_birth"].max() + 0.01],
            color="Race/Ethnicity",
            title="San Diego Region: Fertility Rates",
            labels={"rate_birth": "", "Race/Ethnicity": ""},
            line_shape="spline",
        ).update_layout(legend=dict(orientation="h", y=1.15))

        st.plotly_chart(fig)

        # Calculate rate-based total fertiliy rate for all race/ethnicity groups
        tfr = (
            fertility.groupby("Race/Ethnicity")["rate_birth"]
            .sum()
            .reset_index()
            .rename(columns={"rate_birth": "Total Fertility Rate"})
        )

        # Calculate implied TFR for San Diego County using the components of change
        tfr_sd = (
            pd.read_csv("output/components.csv")
            .query("year == @tab3_1_year & sex == 'F'")
            .merge(
                right=pd.read_csv("output/population.csv"),
                on=["year", "race", "sex", "age"],
            )
            .groupby("age")[["births", "pop"]]
            .sum()
            .assign(rate_birth=lambda x: x["births"] / x["pop"])["rate_birth"]
            .sum()
        )

        # Display total fertiliy rates
        st.dataframe(
            pd.concat(
                [
                    tfr,
                    pd.DataFrame(
                        {
                            "Race/Ethnicity": "San Diego County",
                            "Total Fertility Rate": tfr_sd,
                        },
                        index=[0],
                    ),
                ],
                ignore_index=True,
            ),
            hide_index=True,
            column_config={
                "Total Fertility Rate": st.column_config.NumberColumn(
                    format="localized"
                )
            },
        )

    # Mortality Rates
    with tab3_2:
        # Load mortality rate data
        mortality = pd.read_csv("output/rates.csv")[
            ["year", "race", "sex", "age", "rate_death"]
        ].rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})

        # Create year slider to filter dataset
        tab3_2_year = st.slider(
            label="**Forecast Year:**",
            min_value=mortality["Year"].min(),
            max_value=mortality["Year"].max(),
            key="tab3_2_year",
        )

        # Create sex selector and filter line chart
        tab3_2_sex = st.pills(
            label="**Sex:**",
            options=["M", "F"],
            selection_mode="single",
            default="M",
            key="tab3_2_sex",
        )

        mortality = mortality.query("Year == @tab3_2_year & sex == @tab3_2_sex")

        # Show mortality rates in a line chart
        fig = px.line(
            mortality,
            x="Age",
            y="rate_death",
            range_x=[0, 110],
            range_y=[0, mortality["rate_death"].max() + 0.01],
            color="Race/Ethnicity",
            title="San Diego Region: Mortality Rates",
            labels={"rate_death": "", "Race/Ethnicity": ""},
            line_shape="spline",
        ).update_layout(legend=dict(orientation="h", y=1.15))

        st.plotly_chart(fig)

        # Calculate rate-based life expectancy for all race/ethnicity groups
        lfe = (
            mortality.groupby("Race/Ethnicity")["rate_death"]
            .apply(lambda x: utils.life_expectancy(q_x=x.tolist(), age=0))
            .reset_index(0)
        ).rename(columns={"rate_death": "Life Expectancy"})

        # Calculate implied life expectancy for San Diego County using the components of change
        lfe_sd = utils.life_expectancy(
            q_x=(
                pd.read_csv("output/components.csv")
                .query("year == @tab3_2_year & sex == @tab3_2_sex")
                .merge(
                    right=pd.read_csv("output/population.csv"),
                    on=["year", "race", "sex", "age"],
                )
                .groupby("age")[["deaths", "pop"]]
                .sum()
                .assign(rate_death=lambda x: x["deaths"] / x["pop"])["rate_death"]
                .fillna(0)  # implied mortality rates for 0 population categories
            ).tolist(),
            age=0,
        )

        # Display life expectancy
        st.dataframe(
            pd.concat(
                [
                    lfe,
                    pd.DataFrame(
                        {
                            "Race/Ethnicity": "San Diego County",
                            "Life Expectancy": lfe_sd,
                        },
                        index=[0],
                    ),
                ],
                ignore_index=True,
            ),
            hide_index=True,
            column_config={
                "Life Expectancy": st.column_config.NumberColumn(format="localized")
            },
        )

    # Migration Rates
    with tab3_3:
        # Load migration rate data
        migration = (
            pd.read_csv("output/rates.csv")[
                ["year", "race", "sex", "age", "rate_in", "rate_out"]
            ]
            .rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})
            .assign(rate_net=lambda x: x["rate_in"] - x["rate_out"])
        )

        # Create year slider to filter dataset
        tab3_3_year = st.slider(
            label="**Forecast Year:**",
            min_value=migration["Year"].min(),
            max_value=migration["Year"].max(),
            key="tab3_3_year",
        )

        # Create sex selector and filter line chart
        tab_3_3_sex = st.pills(
            label="**Sex:**",
            options=["M", "F"],
            selection_mode="single",
            default="M",
            key="tab_3_3_sex",
        )

        migration = migration.query("Year == @tab3_3_year & sex == @tab_3_3_sex")

        # Show net migration rates in a line chart
        fig = px.line(
            migration,
            x="Age",
            y="rate_net",
            range_x=[0, 110],
            range_y=[
                -abs(migration["rate_net"]).max() - 0.01,
                abs(migration["rate_net"]).max() + 0.01,
            ],
            color="Race/Ethnicity",
            title="San Diego Region: Net Migration Rates",
            labels={"rate_net": "", "Race/Ethnicity": ""},
            line_shape="spline",
        ).update_layout(legend=dict(orientation="h", y=1.15))

        st.plotly_chart(fig)

        # Display the Race/Ethnicity composition of migrants in a table
        migrants = (
            pd.read_csv("output/components.csv")
            .query("year == @tab3_3_year & sex == @tab_3_3_sex")
            .groupby("race")[["ins", "outs"]]
            .sum()
            .assign(net=lambda x: x["ins"] - x["outs"])
            .reset_index()
            .rename(
                columns={
                    "race": "Race/Ethnicity",
                    "net": "Net Migrants",
                    "ins": "In-Migrants",
                    "outs": "Out-Migrants",
                }
            )
        )

        st.dataframe(
            migrants,
            hide_index=True,
            column_order=[
                "Race/Ethnicity",
                "Net Migrants",
                "In-Migrants",
                "Out-Migrants",
            ],
            column_config={
                "Net Migrants": st.column_config.NumberColumn(format="localized"),
                "In-Migrants": st.column_config.NumberColumn(format="localized"),
                "Out-Migrants": st.column_config.NumberColumn(format="localized"),
            },
        )
