import streamlit as st
import pandas as pd
import plotly.express as px
import utils

# Load data
population_data = pd.read_csv("output/population.csv")
components_data = pd.read_csv("output/components.csv")
rates_data = pd.read_csv("output/rates.csv")

# Rates
# Sub-tabs for fertility, mortality, and migration rates
tab1, tab2, tab3 = st.tabs(["Fertility", "Mortality", "Migration"])

# Fertility Rates
with tab1:
    # Load fertility rate data
    fertility = (
        rates_data[
            ["year", "race", "sex", "age", "rate_birth"]
        ]
        .query("age >= 15 & age <= 45")
        .rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})
    )

    # Create year slider and filter dataset
    tab1_year = st.slider(
        label="**Forecast Year:**",
        min_value=fertility["Year"].min(),
        max_value=fertility["Year"].max(),
        key="tab1_year",
    )

    fertility = fertility.query("Year == @tab1_year")

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
        components_data
        .query("year == @tab1_year & sex == 'F'")
        .merge(
            right=population_data,
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
with tab2:
    # Load mortality rate data
    mortality = rates_data[
        ["year", "race", "sex", "age", "rate_death"]
    ].rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})

    # Create year slider to filter dataset
    tab2_year = st.slider(
        label="**Forecast Year:**",
        min_value=mortality["Year"].min(),
        max_value=mortality["Year"].max(),
        key="tab2_year",
    )

    # Create sex selector and filter line chart
    tab2_sex = st.pills(
        label="**Sex:**",
        options=["M", "F"],
        selection_mode="single",
        default="M",
        key="tab2_sex",
    )

    mortality = mortality.query("Year == @tab2_year & sex == @tab2_sex")

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
            components_data
            .query("year == @tab2_year & sex == @tab2_sex")
            .merge(
                right=population_data,
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
with tab3:
    # Load migration rate data
    migration = (
        rates_data[
            ["year", "race", "sex", "age", "rate_in", "rate_out"]
        ]
        .rename(columns={"year": "Year", "race": "Race/Ethnicity", "age": "Age"})
        .assign(rate_net=lambda x: x["rate_in"] - x["rate_out"])
    )

    # Create year slider to filter dataset
    tab3_year = st.slider(
        label="**Forecast Year:**",
        min_value=migration["Year"].min(),
        max_value=migration["Year"].max(),
        key="tab3_year",
    )

    # Create sex selector and filter line chart
    tab3_sex = st.pills(
        label="**Sex:**",
        options=["M", "F"],
        selection_mode="single",
        default="M",
        key="tab3_sex",
    )

    migration = migration.query("Year == @tab3_year & sex == @tab3_sex")

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
        components_data
        .query("year == @tab3_year & sex == @tab3_sex")
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
            k: st.column_config.NumberColumn(format="localized")
            for k in [
                "Net Migrants",
                "In-Migrants",
                "Out-Migrants",
            ]
        },
    )