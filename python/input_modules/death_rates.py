"""Get death rates by single year of age and race/ethnicity."""

import logging
import scipy

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

logger = logging.getLogger(__name__)


def load_cdc_wonder(population: pd.DataFrame, year: int) -> pd.DataFrame:
    """Load CDC WONDER mortality file from SQL and transform into a standardized DataFrame.

    This function loads mortality data from SQL and replaces San Diego Countypopulation
    with CCM population for the 2018+ product to fill in missing population values for
    the county, and then inflates deaths using the inflation factor calculated from the
    number of "Not Stated" deaths.

    Args:
        population (pd.DataFrame): Population DataFrame to merge with CDC WONDER data
        year (int): The year to load data for.

    Returns:
        pd.DataFrame: Processed DataFrame with no missing or 'Not Stated' values.
    """

    with utils.CCM_ENGINE.connect() as con:
        # Load CDC WONDER data from database for the specific year only
        with open(utils.SQL_FOLDER / "mortality" / "cdc_wonder_mortality.sql") as file:
            cdc_wonder = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=con,
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
                con=con,
                params={"year": year},
            )
            logger.info("CDC WONDER mortality inflation factors loaded from database:")

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
    return (
        pd.merge(cdc_wonder, inflation_factor, on=["location", "sex"])
        .assign(
            deaths=lambda x: x["deaths"] * x["inflation_factor"],
            rates=lambda x: np.where(
                (x["deaths"].isnull()) | (x["pop"] <= 0), np.nan, x["deaths"] / x["pop"]
            ),
        )
        .drop(columns=["inflation_factor"])
    )


def deaths_recode(deaths: int, pop: int) -> float:
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


def substitute_geographies(population: pd.DataFrame, year: int) -> pd.DataFrame:
    """Substitute missing or suppressed geographies with higher-level data.

    Supplements county-level data with state- or national-level equivalents
    when values are unavailable or suppressed.

    Args:
        population (pd.DataFrame): Population dataframe from CCM for 2018+
            product population estimates
        year (int): The year to load data for

    Returns:
        pd.DataFrame: A single DataFrame for ages 0-85 with mortality rates.
    """

    # Use unified load_cdc_wonder function with year parameter
    df = load_cdc_wonder(population=population, year=year)

    if df.empty:
        raise ValueError(f"No CDC WONDER data found for year {year}")

    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        df.pivot_table(
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
        np.vectorize(deaths_recode)(nat_deaths, nat_pop) / nat_pop,
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


def smooth_rates(input_df: pd.DataFrame, s: int, k: int) -> pd.DataFrame:
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
        >>> df_smooth = smooth_rates(df, s=5, k=2)
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


def calculate_death_rates(
    year: int,
    population: pd.DataFrame,
    smooth_s: int = 5,
    smooth_k: int = 2,
) -> pd.DataFrame:
    """Calculate mortality rates by single year of age, sex, and race/ethnicity.

    Mortality rates are calculated for ages < 85 from CDC WONDER by simply
    dividing raw deaths by population for each single year of age, sex, and
    race/ethnicity category after setting "Suppressed" raw deaths (values < 10)
    to values of 4.5 and 0 raw deaths to values of 1. This strategy avoids
    missing value records and implausible 0% mortality rates.

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

    Args:
        year (int): Increment year.
        population (pd.DataFrame): Population data for the year.
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.

    Returns:
        pd.DataFrame: Mortality rates broken down by single year of age, sex, and
            race.
    """
    # Load mortality data for this specific year
    cdc_data = substitute_geographies(population=population, year=year)[
        ["age", "sex", "ethnicity", "rates"]
    ]

    # Load UNDESA data for ages 85-99
    with utils.CCM_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "mortality" / "undesa_survivors.sql") as file:
            undesa_rates = pd.read_sql_query(
                sql=sql.text(file.read()), con=con, params={"year": year}
            )
            logger.info("UN DESA loaded from database:")

    # Expand UNDESA rates to include all race/ethnicity categories
    # UN DESA life table does not have race/ethnicity, apply same rates to all
    race_categories = cdc_data["ethnicity"].unique()
    undesa_expanded = []
    for race in race_categories:
        undesa_race = undesa_rates.copy()
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
        combined_rates = smooth_rates(input_df=combined_rates, s=smooth_s, k=smooth_k)

    # Rename to final column name
    rates = combined_rates.rename(columns={"rates": "rate_death"})

    # Validate output has correct structure
    tests.validate_data(
        table_name=f"Mortality Rates (year {year})",
        data=rates[["age", "sex", "ethnicity", "rate_death"]],
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

    return rates[["age", "sex", "ethnicity", "rate_death"]]


def get_death_rates(year: int, population: pd.DataFrame) -> pd.DataFrame:
    """Create mortality rates by single year of age, sex, and race/ethnicity.

    For the launch year, calculate the crude death rate within single year of
    age, sex, and race/ethnicity. Post launch year, if mortality rates are
    provided, use them. Otherwise, the function should not be called.

    Args:
        year (int): Increment year
        population (pd.DataFrame): Population data by single year of age, sex,
            and race/ethnicity

    Returns:
        pd.DataFrame: Mortality rates by single year of age, sex, and
            race/ethnicity
    """
    # Mortality rates calculated for the launch year
    if year == utils.LAUNCH_YEAR:
        return calculate_death_rates(year=year, population=population)

    # Mortality rates are not calculated past the launch year
    # Post-launch rates are used directly if provided
    else:
        if utils.MORTALITY_RATES is not None:
            # Use the provided rates directly
            return utils.MORTALITY_RATES.loc[utils.MORTALITY_RATES["year"] == year][
                ["age", "sex", "ethnicity", "rate_death"]
            ]
        else:
            raise ValueError(
                "Function called post launch year but mortality rates not provided."
            )
