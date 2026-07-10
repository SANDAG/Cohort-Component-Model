import logging
import scipy

import numpy as np
import pandas as pd

import python.utils as utils

logger = logging.getLogger(__name__)


def load_cdc_wonder(pop_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Load CDC WONDER mortality file from SQL and transform into a standardized DataFrame.

    This function performs several key transformations to prepare the CDC WONDER 
    mortality data for analysis:
    - It locates the number of not stated deaths versus stated deaths for a specific 
      year, separated by geography and sex, then calculates an inflation factor.
    - Creates "Native Hawaiian or Other Pacific Islander alone" and "Two or More Races" 
      from missing race records.
    - Removes "Not Stated" records from the dataset.
    - For the 2018+ product, replaces San Diego County population with CCM population to
      fill in missing population values for the county.

    Args:
        pop_df (pd.DataFrame): Population DataFrame to merge with CDC WONDER data.
        year (int): The year to load data for.

    Returns:
        pd.DataFrame: Processed DataFrame with no missing or 'Not Stated' values.
    """

    with utils.SQL_ENGINE.connect() as con:
        # Load CDC WONDER data from database for the specific year only
        with open(utils.ROOT_FOLDER / "sql" / "cdc_wonder_mortality.sql") as file:
            cdc_wonder = pd.read_sql_query(
                sql=file.read(),
                con=con,
            )
            print("CDC WONDER mortality data loaded from database:")
    
    # Filter to specific year BEFORE calculating inflation factor
    cdc_wonder = cdc_wonder[cdc_wonder["year"] == year]

    cdc_wonder = cdc_wonder.assign(
        # Convert sex to M/F early to match original code convention
        sex=lambda x: x["sex"].replace({"Female": "F", "Male": "M"}),
        # Files with race="All" & hispanic="Hispanic or Latino" represent Hispanic data
        race=lambda x: np.where(
            x["hispanic_origin"] == "Hispanic or Latino",
            "Hispanic",
            x["race"]
        ),
        # Convert 2022+ San Diego County 5-year average deaths to annual deaths
        # Population for 2022+ county level is suppressed and will be replaced
        # with yearly CCM population estimates which require annual death counts to
        # calculate rates
        deaths=lambda x: pd.to_numeric(x["deaths"], errors="coerce") / np.where(
            (x["year"] >= 2022) & (x["location"] == "San Diego County"),
            5,
            1
        ),
    ).replace(
            {
                "Asian": "Asian alone",
                "Asian or Pacific Islander": "Asian alone",
                "Black or African American": "Black or African American alone",
                "American Indian or Alaska Native": "American Indian or Alaska Native "
                "alone",
                "More than one race": "Two or More Races",
                "White": "White alone",
                "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other "
                "Pacific Islander alone",
                "85+": 85
            }
    )
    
    # Separate not stated and stated records
    ns = (
        cdc_wonder[(cdc_wonder["age"] == "Not Stated") | (cdc_wonder["hispanic_origin"] 
                                                          == "Not Stated")]
        .groupby(["location", "sex"], as_index=False)["deaths"]
        .sum()
    )

    stated = (
        cdc_wonder[(cdc_wonder["age"] == "All Stated Ages")]
        .groupby(["location", "sex"], as_index=False)["deaths"]
        .sum()
    )

    # Merge and create inflation factor
    inflation_factor = pd.merge(
        ns,
        stated,
        on=["location", "sex"],
        suffixes=("_not_stated", "_stated"),
    ).assign(
        inflation_factor=lambda x: 1 + (x["deaths_not_stated"] / x["deaths_stated"])
    )[
        ["location", "sex", "inflation_factor"]
    ]

    # Remove "Not Stated" records 
    cdc_wonder = cdc_wonder[
        (cdc_wonder["age"] != "Not Stated") &
        (cdc_wonder["age"] != "All Stated Ages") &
        (cdc_wonder["hispanic_origin"] != "Not Stated") 
    ].reset_index(drop=True)

    # Convert age to numeric after filtering out "Not Stated"
    cdc_wonder["age"] = pd.to_numeric(cdc_wonder["age"])

    # Duplicate 'All Races' records into NHPI and MOR for years <= 2020 only
    # For years >= 2022, actual race-specific files with sufficient data exist
    # Note: Records where race is "All Races" both represent aggregate data
    all_races = cdc_wonder[cdc_wonder["race"] == "All Races"]
    cdc_wonder = cdc_wonder[cdc_wonder["race"].notnull() & (cdc_wonder["race"] != 
                                                            "All Races")]

    # Only duplicate if THIS YEAR is <= 2020
    if year <= 2020:
        result = pd.concat(
            [
                cdc_wonder,
                all_races.assign(
                    race="Native Hawaiian or Other Pacific Islander alone"
                ),
                all_races.assign(race="Two or More Races"),
            ],
            ignore_index=True,
        ) 
    else:
        result = cdc_wonder
    
    # Remove "All Races" category after using it to create NHPI and Two or More Races
    result = result[result["race"] != "All Races"].reset_index(drop=True)

    # For the 2018+ product, merge SD County deaths with CCM population
    if (result["product"] == "2018+").any() and pop_df is not None:

        # Separate SYA (ages 0-84) and TYA (age 85) records
        sya_records = result[result["age"] < 85].copy()
        tya_records = result[result["age"] == 85].copy()
        
        # For SYA records (ages 0-84), use direct age match
        if len(sya_records) > 0:
            sya_records = (
                sya_records.merge(pop_df[["age", "sex", "race", "pop"]], on=["age", 
                                "sex", "race"], how="left", suffixes=("", "_ccm"))
                .assign(pop=lambda x: np.where(
                    x["location"] == "San Diego County",
                    x["pop_ccm"].fillna(x["pop"]),
                    x["pop"]
                ))
                .drop(columns=["pop_ccm"])
            )
        
        # For TYA records (age 85 = ages 85-99), sum population across age range
        if len(tya_records) > 0:
            pop_85plus = (
                pop_df.loc[pop_df["age"].between(85, 99)][
                    ["sex", "race", "pop"]
                ]
                .groupby(["sex", "race"], as_index=False)["pop"]
                .sum()
                .assign(age=85)
            )

            tya_records = (
                tya_records.merge(pop_85plus, on=["age", "sex", "race"], how="left", 
                                  suffixes=("", "_ccm"))
                .assign(pop=lambda x: np.where(
                    x["location"] == "San Diego County",
                    x["pop_ccm"].fillna(x["pop"]),
                    x["pop"]
                ))
                .drop(columns=["pop_ccm"])
            )
        
        # Combine back together
        result = pd.concat([sya_records, tya_records], ignore_index=True)

    # Inflate deaths and calculate rates for all ages
    final = (
        pd.merge(result, inflation_factor, on=["location", "sex"])
        .assign(
            deaths=lambda x: x["deaths"] * x["inflation_factor"],
            rates=lambda x: np.where(
                x["deaths"].isnull(), np.nan, x["deaths"] / x["pop"]
            ),
        )
        .drop(columns=["inflation_factor"])
    )

    return final


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


def load_local_files(pop_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Load files from a directory for a specific year and combine them by product.

    This function performs the geography substitution, supplementing data from a higher
    geography when data is missing or suppressed.

    Args:
        pop_df (pd.DataFrame): Population dataframe from CCM for 2018+ product
            population estimates.
        year (int): The year to load data for.

    Returns:
        pd.DataFrame: A single DataFrame for ages 0-85 with mortality rates.
    """

    # Use unified load_cdc_wonder function with year parameter
    df = load_cdc_wonder(pop_df, year)

    if year == 2021:
        logger.warning("CDC WONDER data unavailable for 2021. Using 2020 data.")
    
    if df.empty:
        raise ValueError(f"No CDC WONDER data found for year {year}")
    
    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        df.pivot_table(
            index=["year", "age", "race", "sex", "hispanic_origin"],
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

    # For NHPI, use State > National
    # Mix of NHPI county and state level data causes discontinuity in rates
    pivoted["rates"] = np.where(
        pivoted["race"] == "Native Hawaiian or Other Pacific Islander alone",
        np.where(
            (state.notna()) & (state > 0),
            state,
            np.where(
                (national.notna()) & (national > 0),
                national,
                national_impute,
            ),
        ),
        # For all other races: County > State > National hierarchy
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
    df = (
        pivoted[["year", "age", "race", "sex", "rates"]]
        .sort_values(by=["sex", "race", "year", "age"])
        .reset_index(drop=True)
    )

    return df


def smooth_rates(input_df: pd.DataFrame, s: int, k: int) -> pd.DataFrame:
    """Smooth mortality rates using spline interpolation.

    This function replaces mortality rates with smoothed values by applying
    spline interpolation across ages for each unique combination of grouping
    variables (sex, race/ethnicity, year). The smoothing is applied to the
    natural logarithm of the rates to ensure non-negativity and better handle
    the exponential nature of mortality rates.

    Args:
        input_df (pd.DataFrame): DataFrame containing mortality rates with
            columns 'age', 'rates', 'sex', 'race', and 'year'.
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
        >>> df_custom = smooth_rates(df, s=10, k=3, group_cols=["year", "region"])
    """
    # Validate required columns
    required_cols = ["age", "rates", "sex", "race", "year"]
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
        for race in df["race"].unique():
            for year in df["year"].unique():
                mask = (df["sex"] == sex) & (df["race"] == race) & (df["year"] == year)

                # Get subset and sort by age
                subset = df.loc[mask, ["age", "rates"]].copy()
                subset = subset.sort_values("age")

                # Fit spline to log rates
                spline = scipy.interpolate.make_splrep(
                    subset["age"], np.log(subset["rates"]), s=s, k=k
                )

                # Evaluate spline to get smoothed rates
                smoothed_rates = np.exp(scipy.interpolate.splev(subset["age"], spline))

                # Update rates in the DataFrame using boolean indexing
                df.loc[subset.index, "rates"] = smoothed_rates

    return df


def process_life_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Create five-year moving average rate for each race/ethnicity in CDC WONDER.

    The survivors dataset from UN DESA does not contain data for races nor does it have
    any moving averages. To be appended to the CDC WONDER data, races are added into the
    dataset and five-year moving averages are calculated for each rate.

    Args:
        df (pd.DataFrame): The cleaned Survivors Life Table dataset.

    Returns:
        pd.DataFrame: A DataFrame containing the five-year moving averaged rates and
            races matching the CDC WONDER.
    """

    df = (
        df.assign(
            deaths=lambda x: (
                x["survivors"] - x.groupby(["year", "sex"])["survivors"].shift(-1)
            ),
        )
        .assign(
            deaths=lambda x: x.groupby(["sex", "age"])["deaths"]
            .transform(lambda x: x.rolling(window=5, min_periods=5).sum())
            .astype("float64"),
            survivors=lambda x: x.groupby(["sex", "age"])["survivors"]
            .transform(lambda x: x.rolling(window=5, min_periods=5).sum())
            .astype("float64"),
        )
        .assign(rates=lambda x: (x["deaths"] / x["survivors"]).astype("float64"))
        .query("year >= 2003 and age >= 85 and age < 100")
        .reset_index(drop=True)
    )

    return df

def get_death_rates(
    yr: int,
    pop_df: pd.DataFrame,
    smooth_s: int = 5,
    smooth_k: int = 2,
) -> pd.DataFrame:
    """Create death rates broken down by race, sex, and single year of age.

    Death rates are calculated for ages < 85 from CDC WONDER by simply
    dividing raw deaths by population for each race, sex, and single year of
    age category after setting "Suppressed" raw deaths (values < 10) to values
    of 4.5 and 0 raw deaths to values of 1. This strategy avoids missing value
    records and implausible 0% death rates.

    For ages >= 85, UN DESA life table data is used. UN DESA provides mortality
    rates by sex and age but not by race. To incorporate race-specific variation,
    scaling factors are calculated using CDC TYA (Ten-Year Age) 85+ rates by race/sex.
    The scaling factor for each race/sex combination equals the CDC 85+ rate divided
    by the aggregate UN DESA 85-99 rate. This scaling factor is then applied to each
    individual UN DESA age (85-99) to produce race-specific rates that match CDC's
    overall 85+ mortality pattern by race.

    The CDC WONDER dataset for 2021 is unavailable, so 2020 data is used
    as a substitute for year 2021.

    Smoothing is applied to the combined CDC and scaled UN DESA dataset.

    Args:
        yr: Increment year.
        pop_df (pd.DataFrame): Population data for the year.
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.

    Returns:
        pd.DataFrame: Death rates broken down by race, sex, and single year
            of age.
    """
    # Load and process CDC WONDER mortality data
    # Determine which year's data to use (2021 uses 2020 data)
    cdc_yr = 2020 if yr == 2021 else yr
    if yr == 2021:
        logger.warning("CDC WONDER data unavailable for 2021. Using 2020 data.")

    # Load mortality data for this specific year
    cdc_data = load_local_files(pop_df=pop_df, year=cdc_yr)[
        ["race", "sex", "age", "rates"]
    ]

    # Load UNDESA data for ages 85-99
    with utils.SQL_ENGINE.connect() as con:
        with open(utils.ROOT_FOLDER / "sql" / "undesa_survivors.sql") as file:
            undesa_data = pd.read_sql_query(
                sql=file.read(),
                con=con,
            ).loc[lambda df: df["year"] >= 1999].assign(
                sex=lambda x: x["sex"].replace({"Female": "F", "Male": "M"})
            )
    
    # Convert age to numeric and sort
    undesa_data = (
        undesa_data
        .assign(age=lambda x: x["age"].replace("100+", "100").astype("int64"))
        .sort_values(["year", "sex", "age"])
        .reset_index(drop=True)
    )

    # Process UNDESA data for ages 85-99
    undesa_rates = process_life_rates(undesa_data)

    # Use the latest available year from UNDESA data
    max_undesa_year = undesa_rates["year"].max()
    undesa_yr = min(cdc_yr, max_undesa_year)
    if cdc_yr > max_undesa_year:
        logger.warning(
            f"UN DESA data unavailable for {cdc_yr}. Using {max_undesa_year} data for "
            f"ages 85-99."
        )
    undesa_rates = undesa_rates[undesa_rates["year"] == undesa_yr][
        ["sex", "age", "rates", "deaths", "survivors"]
    ]

    # Expand UNDESA rates to include all race categories
    # UN DESA life table doesn't have race breakdown, so apply same rates to all
    race_categories = cdc_data["race"].unique()
    undesa_expanded = []
    for race in race_categories:
        undesa_race = undesa_rates.copy()
        undesa_race["race"] = race
        undesa_expanded.append(undesa_race)
    undesa_rates = pd.concat(undesa_expanded, ignore_index=True)

    # Get CDC mortality rate for age 85 (from TYA 85+ group)
    cdc_rate_85plus = cdc_data[cdc_data["age"] == 85][
        ["race", "sex", "rates"]
    ].rename(columns={"rates": "cdc_rate"})

    # Calculate UN DESA implied mortality rate and scaling factor
    scaling_df = cdc_rate_85plus.merge(
        undesa_rates.groupby(["sex", "race"], as_index=False)
        .agg({"deaths": "sum", "survivors": "sum"})
        .assign(undesa_rate=lambda x: x["deaths"] / x["survivors"])[
            ["sex", "race", "undesa_rate"]
        ],
        on=["sex", "race"],
        how="left",
    ).assign(scaling_factor=lambda x: x["cdc_rate"] / x["undesa_rate"])

    # Merge scaling factor and apply to UNDESA mortality rates
    undesa_rates = (
        undesa_rates.merge(
            scaling_df[["sex", "race", "scaling_factor"]],
            on=["sex", "race"],
            how="left",
        )
        .assign(rates=lambda x: x["rates"] * x["scaling_factor"])
        .drop(columns=["scaling_factor"])
    )[["sex", "age", "race", "rates"]]

    cdc_rates = cdc_data[cdc_data["age"] < 85]

    # Combine CDC rates (ages 0-84) with scaled UNDESA rates (ages 85-99)
    combined_rates = pd.concat([cdc_rates, undesa_rates], ignore_index=True)

    # Apply smoothing to the combined dataset (ages 0-99)
    if smooth_s is not None and smooth_k is not None:
        # Prepare combined DataFrame for smooth_rates function
        combined_rates["year"] = cdc_yr

        # Apply smoothing to full age range
        combined_rates = smooth_rates(combined_rates, s=smooth_s, k=smooth_k)

    # Rename to final column name
    rates = combined_rates.rename(columns={"rates": "rate_death"})

    return rates[["race", "sex", "age", "rate_death"]]
