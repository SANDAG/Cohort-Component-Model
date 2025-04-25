import streamlit as st
import pandas as pd
import plotly.express as px
import utils

# Cached data loaders
@st.cache_data
def load_population() -> pd.DataFrame:
    return pd.read_csv("output/population.csv")

@st.cache_data
def load_components() -> pd.DataFrame:
    return pd.read_csv("output/components.csv")

@st.cache_data
def load_rates() -> pd.DataFrame:
    return pd.read_csv("output/rates.csv")

# Load data
population_data = load_population()
components_data = load_components()
rates_data = load_rates()

# Rates
# Sub-tabs for fertility, mortality, and migration rates
tab3_1, tab3_2, tab3_3 = st.tabs(["Fertility", "Mortality", "Migration"])

# Fertility Rates
with tab3_1:
    # Load fertility rate data
    fertility = (
        rates_data[
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
    fig = utils.plot_line_chart(
        fertility,
        x="Age",
        y="rate_birth",
        x_range=[15, 45],
        y_range=[0, fertility["rate_birth"].max() + 0.01],
        color="Race/Ethnicity",
        title="San Diego Region: Fertility Rates"
    )

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
        .query("year == @tab3_1_year & sex == 'F'")
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
with tab3_2:
    # Load mortality rate data
    mortality = rates_data[
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
    fig = utils.plot_line_chart(
        mortality,
        x="Age",
        y="rate_death",
        x_range=[0, 110],
        y_range=[0, mortality["rate_death"].max() + 0.01],
        color="Race/Ethnicity",
        title="San Diego Region: Mortality Rates"
    )

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
            .query("year == @tab3_2_year & sex == @tab3_2_sex")
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
with tab3_3:
    # Load migration rate data
    migration = (
        rates_data[
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
    fig = utils.plot_line_chart(
        migration,
        x="Age",
        y="rate_net",
        x_range=[0, 110],
        y_range=[
            -abs(migration["rate_net"]).max() - 0.01,
            abs(migration["rate_net"]).max() + 0.01,
        ],
        color="Race/Ethnicity",
        title="San Diego Region: Net Migration Rates"
    )

    st.plotly_chart(fig)

    # Display the Race/Ethnicity composition of migrants in a table
    migrants = (
        components_data
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
            k: st.column_config.NumberColumn(format="localized")
            for k in [
                "Net Migrants",
                "In-Migrants",
                "Out-Migrants",
            ]
        },
    )