"""Get death rates by single year of age, sex, and race/ethnicity."""

import logging
import scipy

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

logger = logging.getLogger(__name__)


def run_mortality_rates(year: int, population: pd.DataFrame) -> pd.DataFrame:
    """Orchestrator function to calculate mortality rates.

    This module generates mortality rates by single year of age, sex, and race/ethnicity
    using data from the Centers for Disease Control and Prevention (CDC) WONDER
    mortality database.

    Mortality rates are calculated for ages < 85 from CDC WONDER by simply
    dividing raw deaths by population for each single year of age, sex, and
    race/ethnicity category after setting "Suppressed" raw deaths (values < 10)
    to values of 4.5 and 0 raw deaths to values of 1. This strategy avoids
    missing value records and implausible 0% mortality rates. Any missing
    county-level fertility rates are substituted following a county, state, then national
    hierarchy. Should there be no county-, state-, or national-level data available,
    a separate recoding formula will be used (see _deaths_recode function for details).

    For ages >= 85, UN DESA life table data is used. UN DESA provides mortality
    rates by age and sex, but not by race/ethnicity. To incorporate race-specific
    variation,scaling factors are calculated using CDC TYA (Ten-Year Age) 85+
    mortality rates by sex and race/ethnicity. The scaling factor for each
    sex and race/ethnicity combination equals the CDC 85+ mortality rate divided
    by the aggregate UN DESA 85-99 rate. This scaling factor is then applied to
    each individual UN DESA age (85-99) to produce race/ethnicity-specific
    mortality rates that match CDC's overall 85+ mortality pattern by
    race/ethnicity.

    The CDC WONDER mortality dataset for 2021 is unavailable, so 2020 data is
    used as a substitute for year 2021. Smoothing is applied to the combined
    CDC and scaled UN DESA dataset.

    Functionality is split apart for code encapsulation:
        _get_mortality_inputs - Get deaths by age, sex, and ethnicity from CDC WONDER
            mortality database
        _validate_mortality_inputs - Validate inputs from the above function
        _create_mortality_outputs - Calculate mortality rates by single year of age,
            sex, and race/ethnicity; replace missing San Diego County population with
            launch year population for years 2022 and onward (2018+ CDC Product);
            inflate deaths using the inflation factor; scale UN DESA 85+ mortality rates
            to match CDC 85+ mortality patterns by race/ethnicity
        _validate_mortality_outputs - Validate the output from the above function
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating mortality rates for launch year")

        mortality_rates_inputs = _get_mortality_inputs(year, population)
        _validate_mortality_inputs(
            mortality_rates_inputs["mortality_inputs"],
            mortality_rates_inputs["undesa_rates"],
        )

        mortality_outputs = _create_mortality_outputs(mortality_rates_inputs)
        _validate_mortality_outputs(mortality_outputs)

        return mortality_outputs
    else:
        if utils.MORTALITY_RATES is not None:
            # Use the provided rates directly
            return utils.MORTALITY_RATES.loc[utils.MORTALITY_RATES["year"] == year][
                ["age", "sex", "ethnicity", "rate_death"]
            ]
        else:
            raise ValueError("No mortality rates provided post-launch year.")


def _get_mortality_inputs(
    year: int, population: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """Retrieve mortality inputs from the CDC WONDER database for a given year."""
    with utils.CCM_ENGINE.connect() as connection:
        # Load CDC WONDER data from database for the specific year only
        with open(utils.SQL_FOLDER / "mortality" / "cdc_wonder_mortality.sql") as file:
            cdc_wonder = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )
            # Convert age to integer type
            cdc_wonder["age"] = cdc_wonder["age"].astype(float)
            logger.info("CDC WONDER mortality data loaded from database:")

        # Load inflation factors
        with open(
            utils.SQL_FOLDER / "mortality" / "cdc_wonder_mortality_inflation.sql"
        ) as file:
            inflation_factor = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )
            logger.info("CDC WONDER mortality inflation factors loaded from database:")

        # Load UNDESA data for ages 85-99
        with open(utils.SQL_FOLDER / "mortality" / "undesa_survivors.sql") as file:
            undesa_rates = utils.read_sql_query_fallback(
                max_lookback=2,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )
            logger.info("UN DESA loaded from database:")

    # For years >= 2022 (2018+ product), merge SD County deaths with CCM population
    if year >= 2022 and population is not None:

        # Separate SYA (ages 0-84) and TYA (age 85) records
        sya_records = cdc_wonder[cdc_wonder["age"] < 85].copy()
        tya_records = cdc_wonder[cdc_wonder["age"] == 85].copy()

        # For SYA records (ages 0-84), use direct age match
        if len(sya_records) > 0:
            sya_records = (
                sya_records.merge(
                    population[["age", "sex", "ethnicity", "pop"]],
                    on=["age", "sex", "ethnicity"],
                    how="left",
                    suffixes=("", "_ccm"),
                )
                .assign(
                    pop=lambda x: np.where(
                        x["location"] == "San Diego County",
                        x["pop_ccm"].fillna(x["pop"]),
                        x["pop"],
                    )
                )
                .drop(columns=["pop_ccm"])
            )

        # For TYA records (age 85 = ages 85-99), sum population across age range
        if len(tya_records) > 0:
            pop_85plus = (
                population.loc[population["age"].between(85, 99)][
                    ["sex", "ethnicity", "pop"]
                ]
                .groupby(["sex", "ethnicity"], as_index=False)["pop"]
                .sum()
                .assign(age=85)
            )

            tya_records = (
                tya_records.merge(
                    pop_85plus,
                    on=["age", "sex", "ethnicity"],
                    how="left",
                    suffixes=("", "_ccm"),
                )
                .assign(
                    pop=lambda x: np.where(
                        x["location"] == "San Diego County",
                        x["pop_ccm"].fillna(x["pop"]),
                        x["pop"],
                    )
                )
                .drop(columns=["pop_ccm"])
            )

        # Combine back together
        cdc_wonder = pd.concat([sya_records, tya_records], ignore_index=True)

    # Inflate deaths and calculate rates for all ages
    mortality_inputs = (
        pd.merge(cdc_wonder, inflation_factor, on=["location", "sex"])
        .assign(
            deaths=lambda x: x["deaths"] * x["inflation_factor"],
            rates=lambda x: np.where(
                (x["deaths"].isnull()) | (x["pop"] <= 0),
                np.nan,
                x["deaths"] / x["pop"],
            ),
        )
        .drop(columns=["inflation_factor"])
    )

    return {
        "mortality_inputs": mortality_inputs,
        "undesa_rates": undesa_rates,
    }


def _validate_mortality_inputs(
    mortality_inputs: pd.DataFrame, undesa_rates: pd.DataFrame
) -> None:
    """Validate the mortality inputs."""
    # Validate for each location
    for location in mortality_inputs["location"].unique():
        tests.validate_data(
            table_name=f"Input Mortality Rates for {location}",
            data=mortality_inputs[["age", "sex", "ethnicity"]]
            .loc[mortality_inputs["location"] == location]
            .rename(columns={"age": "age_cdc_deaths"}),
            row_count={"key_columns": {"age_cdc_deaths", "sex", "ethnicity"}},
            negative={"negative_ok": set()},
            null={"null_ok": set()},
        )
    tests.validate_data(
        table_name="Input UN DESA Rates",
        data=undesa_rates[["age", "sex"]].rename(columns={"age": "age_undesa_deaths"}),
        row_count={"key_columns": {"age_undesa_deaths", "sex"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _create_mortality_outputs(
    mortality_inputs: dict[str, pd.DataFrame],
    smooth_s: int = 5,
    smooth_k: int = 2,
) -> pd.DataFrame:
    """Calculate mortality outputs by single year of age, sex, and race/ethnicity.

    Args:
        mortality_inputs (dict[str, pd.DataFrame]): Mortality inputs and inflation
            factors by single year of age, sex, and race/ethnicity
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.

    Returns:
        pd.DataFrame: Mortality outputs by single year of age, sex, and race/ethnicity
    """
    mortality_data = mortality_inputs["mortality_inputs"]
    undesa_data = mortality_inputs["undesa_rates"]

    # Load mortality data for this specific year
    cdc_data = _substitute_geographies(mortality_data)[
        ["age", "sex", "ethnicity", "rates"]
    ]

    # Expand UNDESA rates to include all race/ethnicity categories
    # UN DESA life table does not have race/ethnicity, apply same rates to all
    race_categories = cdc_data["ethnicity"].unique()
    undesa_expanded = []
    for race in race_categories:
        undesa_race = undesa_data.copy()
        undesa_race["ethnicity"] = race
        undesa_expanded.append(undesa_race)
    undesa_rates = pd.concat(undesa_expanded, ignore_index=True)

    # Get CDC mortality rate for age 85 (from TYA 85+ group)
    cdc_rate_85plus = cdc_data[cdc_data["age"] == 85][
        ["sex", "ethnicity", "rates"]
    ].rename(columns={"rates": "cdc_rate"})

    # Get UN DESA mortality rate for age 85+ (aggregate of ages 85-99)
    undesa_rate_85plus = undesa_rates[undesa_rates["age"] == "85+"][
        ["sex", "ethnicity", "rates"]
    ].rename(columns={"rates": "undesa_rate"})

    # Calculate scaling factor
    scaling_df = cdc_rate_85plus.merge(
        undesa_rate_85plus,
        on=["sex", "ethnicity"],
        how="left",
    ).assign(scaling_factor=lambda x: x["cdc_rate"] / x["undesa_rate"])

    # Merge scaling factor and apply to UNDESA mortality rates
    undesa_rates = (
        undesa_rates[undesa_rates["age"] != "85+"]
        .assign(age=lambda x: x["age"].astype(int))
        .merge(
            scaling_df[["sex", "ethnicity", "scaling_factor"]],
            on=["sex", "ethnicity"],
            how="left",
        )
        .assign(rates=lambda x: x["rates"] * x["scaling_factor"])
        .drop(columns=["scaling_factor"])
    )[["age", "sex", "ethnicity", "rates"]]

    cdc_rates = cdc_data[cdc_data["age"] < 85]

    # Combine CDC rates (ages 0-84) with scaled UNDESA rates (ages 85-99)
    combined_rates = pd.concat([cdc_rates, undesa_rates], ignore_index=True)

    # Apply smoothing to the combined dataset (ages 0-99)
    if smooth_s is not None and smooth_k is not None:
        # Apply smoothing to full age range
        combined_rates = _smooth_rates(input_df=combined_rates, s=smooth_s, k=smooth_k)

    # Rename to final column name
    rates = combined_rates.rename(columns={"rates": "rate_death"})

    return rates[["age", "sex", "ethnicity", "rate_death"]]


def _deaths_recode(deaths: int, pop: int) -> float:
    """Recode CDC WONDER zero death and suppressed values.

    This function is used as the final methodology for substituting missing rates where
        deaths are imputed using the following logic:
        - If deaths == 0 and population > 0, return 1 (minimum imputed death count for
            nonzero population)
        - If deaths is NaN (suppressed or missing):
            - If population > 4, return 4.5 (midpoint imputation for suppressed values)
            - If 0 < population <= 4, return 1 (minimum imputation for small population)
            - If population == 0, return 0

        Args:
            deaths (int): The total number of deaths (may be 0, NaN, or a positive
                integer).
            pop (int): The total population.

        Returns:
            float: The recoded (possibly imputed) number of deaths.
    """

    pop = int(pop)  # floor function on floats
    if deaths == 0:
        if pop > 0:
            return 1
        else:
            return 0
    elif pd.isna(deaths):
        if pop > 4:
            return 4.5
        elif pop > 0:
            return 1
        else:
            return 0
    else:
        return float(deaths)


def _substitute_geographies(mortality_inputs: pd.DataFrame) -> pd.DataFrame:
    """Substitute missing or suppressed geographies with higher-level data."""
    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        mortality_inputs.pivot_table(
            index=["age", "sex", "ethnicity"],
            columns="location",
            values=["rates", "deaths", "pop"],
            aggfunc="first",
        )
        .pipe(lambda df: df.set_axis(["_".join(col) for col in df.columns], axis=1))
        .reset_index()
    )

    # Retrieve fields
    county, state, national, nat_deaths, nat_pop = (
        pivoted.get("rates_San Diego County", pd.Series(dtype=float)),
        pivoted.get("rates_California", pd.Series(dtype=float)),
        pivoted.get("rates_United States", pd.Series(dtype=float)),
        pivoted.get("deaths_United States", pd.Series(dtype=float)),
        pivoted.get("pop_United States", pd.Series(dtype=float)),
    )

    # Impute missing or zero rates for national
    national_impute = np.where(
        (nat_pop.notna()) & (nat_pop > 0),
        np.vectorize(_deaths_recode)(nat_deaths, nat_pop) / nat_pop,
        np.nan,
    )

    # For Non-Hispanic, Hawaiian or Pacific Islander, use State > National
    # Mix of county and state level data causes discontinuity in rates
    pivoted["rates"] = np.where(
        pivoted["ethnicity"] == "Non-Hispanic, Hawaiian or Pacific Islander",
        np.where(
            (state.notna()) & (state > 0),
            state,
            np.where(
                (national.notna()) & (national > 0),
                national,
                national_impute,
            ),
        ),
        # For all other race/ethnicity: County > State > National hierarchy
        np.where(
            (county.notna()) & (county > 0),
            county,
            np.where(
                (state.notna()) & (state > 0),
                state,
                np.where(
                    (national.notna()) & (national > 0),
                    national,
                    national_impute,
                ),
            ),
        ),
    )

    # Finalize combined dataset
    return (
        pivoted[["age", "sex", "ethnicity", "rates"]]
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )


def _smooth_rates(input_df: pd.DataFrame, s: int, k: int) -> pd.DataFrame:
    """Smooth mortality rates using spline interpolation.

    This function replaces mortality rates with smoothed values by applying
    spline interpolation across ages for each unique combination of grouping
    variables (sex, ethnicity). The smoothing is applied to the
    natural logarithm of the rates to ensure non-negativity and better handle
    the exponential nature of mortality rates.

    Args:
        input_df (pd.DataFrame): DataFrame containing mortality rates with
            columns 'age', 'sex', 'ethnicity', and 'rates'.
        s (int): Smoothing factor for the spline. Higher values produce
            smoother curves. s=0 means no smoothing (interpolation).
        k (int): Degree of the spline polynomial (1 ≤ k ≤ 5). Common values:
            - k=1: Linear spline
            - k=2: Quadratic spline
            - k=3: Cubic spline (default for many applications)

    Returns:
        pd.DataFrame: DataFrame with smoothed mortality rates. Original
            structure is preserved with only the rate column modified.

    Raises:
        ValueError: If required columns are missing or data is invalid.
        ValueError: If rates contain non-positive values (cannot take log).

    Example:
        >>> df_smooth = _smooth_rates(df, s=5, k=2)
    """
    # Validate required columns
    required_cols = [
        "age",
        "sex",
        "ethnicity",
        "rates",
    ]
    missing_cols = [col for col in required_cols if col not in input_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Check for non-positive rates
    if (input_df["rates"] <= 0).any():
        raise ValueError(
            "Column 'rates' contains non-positive values. "
            "Spline smoothing requires positive rates for log transformation."
        )

    # Avoid overwriting the original DataFrame
    df = input_df.copy()

    for sex in df["sex"].unique():
        for ethnicity in df["ethnicity"].unique():
            mask = (df["sex"] == sex) & (df["ethnicity"] == ethnicity)

            # Get subset and sort by age
            subset = df.loc[mask, ["age", "rates"]].copy().sort_values(by="age")

            # Fit spline to log rates
            spline = scipy.interpolate.make_splrep(
                subset["age"], np.log(subset["rates"]), s=s, k=k
            )

            # Evaluate spline to get smoothed rates
            smoothed_rates = np.exp(scipy.interpolate.splev(subset["age"], spline))

            # Update rates in the DataFrame using boolean indexing
            df.loc[subset.index, "rates"] = smoothed_rates

    return df


def _validate_mortality_outputs(mortality_outputs: pd.DataFrame) -> None:
    """Validate the mortality outputs."""
    # Validate output has correct structure
    tests.validate_data(
        table_name="Output Mortality Rates",
        data=mortality_outputs[["age", "sex", "ethnicity", "rate_death"]],
        row_count={
            "key_columns": {
                "age",
                "sex",
                "ethnicity",
            }
        },
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )
