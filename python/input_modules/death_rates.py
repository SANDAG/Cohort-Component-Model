import logging
import pathlib
import scipy
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def parse_filename(fp: pathlib.Path) -> dict:
    """Parses and validates file name.

    Mortality rate files are downloaded from the NCHS CDC WONDER website.
    https://wonder.cdc.gov/deaths-by-underlying-cause.html

    File names for mortality rates are assumed to follow the structure
    delimited by semicolons with the following parts in order:
    Location; Product; Age Group; Sex; Hispanic; Race; Year; Moving Average

    This function checks that the file name contains exactly 8 parts, that
    each part is in the expected position, and that the values for each part
    are valid based on predefined lists. If any part is missing, extra, or has
    an incorrect value, a ValueError is raised with a descriptive message.

    Args:
        fp (pathlib.Path): The file path to parse and validate

    Raises:
        ValueError: If missing/extra/incorrect parts in file name

    Returns:
        dict: A dictionary of the metadata for the file based on the file name
    """
    # Define expected structure and valid values and map values to their
    # labels in the underlying file content for later validation
    valid_parts = {
        "location": {
            "order": 0,
            "map": {
                "SD": "San Diego County",
                "CA": "California",
                "US": "United States",
            },
        },
        "product": {"order": 1, "map": {"1999-2020": "1999-2020", "2018+": "2018+"}},
        "age_group": {
            "order": 2,
            "map": {"SYA": "Single-Year Ages", "NS": "Not Stated", "ALL": "All"},
        },
        "sex": {"order": 3, "map": {"F": "Female", "M": "Male", "ALL": "All"}},
        "hispanic": {
            "order": 4,
            "map": {
                "HIS": "Hispanic or Latino",
                "NON": "Not Hispanic or Latino",
                "NS": "Not Stated",
                "ALL": "All",
            },
        },
        "race": {
            "order": 5,
            "map": {
                "AIAN": "American Indian or Alaska Native",
                "API": "Asian or Pacific Islander",
                "ASIAN": "Asian",
                "BAA": "Black or African American",
                "MOR": "More than one race",
                "NHPI": "Native Hawaiian or Other Pacific Islander",
                "WH": "White",
                "ALL": "All",
            },
        },
        "year": {
            "order": 6,
            "map": None,
        },  # Accept any year value without restriction
        "moving_average": {"order": 7, "map": {"5Y": "5-Year Moving Average"}},
    }

    # Break file name into parts based on ";" separator
    parts = fp.stem.split("; ")

    if len(parts) != 8:
        raise ValueError(f"Invalid number of parts in file: {fp}")

    metadata = {}
    for key, config in valid_parts.items():
        part_value = parts[config["order"]]  # type: ignore
        if config["map"] is not None and part_value not in config["map"]:
            raise ValueError(
                f"Invalid value for {key}: '{part_value}'. Valid values: {list(config['map'].keys())}"  # type: ignore
            )
        elif config["map"] is not None:
            metadata[key] = config["map"][part_value]  # type: ignore
        else:
            metadata[key] = part_value

    return metadata


def validate_file(fp: pathlib.Path) -> None:
    """Validates file contents against metadata parsed from file name.

    Mortality rate files are downloaded from the NCHS CDC WONDER website.
    https://wonder.cdc.gov/deaths-by-underlying-cause.html

    File names are expected to follow an explicit metadata structure as
    detailed in the parse_filename function. This function verifies the
    contents of the downloaded file match the file name metadata by parsing
    the "Notes" section of the CDC WONDER downloaded file and comparing its
    contents to the metadata implied by the file name.

    Args:
        fp (pathlib.Path): The file path to parse and validate

    Raises:
        ValueError: If missing/extra/incorrect/mismatching metadata and notes
    """

    # Parse and validate the file name to extract metadata
    metadata = parse_filename(fp)

    # Stream the file content to extract query metadata from notes
    notes = {}
    with open(fp, "r") as file:
        for line in file.readlines():
            line = line.strip('"\n')
            if line.startswith("States:"):
                notes["location"] = line.split(":")[1].strip()
            elif line.startswith("Dataset:"):
                notes["product"] = line.split(":")[1].strip()
            elif line.startswith("Sex:"):
                notes["sex"] = line.split(":")[1].strip()
            elif line.startswith("Hispanic Origin:"):
                notes["hispanic"] = line.split(":")[1].strip()
            elif line.startswith("Race:"):
                notes["race"] = line.split(":")[1].strip()
            elif line.startswith("Single Race 6:"):
                notes["race"] = line.split(":")[1].strip()
            elif line.startswith("Year/Month:"):
                notes["year"] = line.split(":")[1].strip()
            elif line.startswith("Single-Year Ages"):
                notes["age_group"] = line
            else:
                pass

    # Location validation is done explicitly for County and State level
    # The United States location will have no information in the notes
    if "location" in notes:
        if metadata["location"] not in notes["location"]:
            raise ValueError(
                f"Metadata location: '{metadata['location']}' Does not match file contents: '{notes['location']}'."
            )
    elif metadata["location"] != "United States":
        raise ValueError(
            f"Metadata location: '{metadata['location']}' does not match file contents: 'United States'."
        )
    else:
        pass

    # Product metadata validation is done explicitly for both products
    # This information is always available in the notes
    if "product" in notes:
        if (
            metadata["product"] == "1999-2020"
            and notes["product"] != "Underlying Cause of Death, 1999-2020"
        ) or (metadata["product"] == "2018+" and "Single Race" not in notes["product"]):
            raise ValueError(
                f"Metadata product: '{metadata['product']}' does not match file contents: '{notes['product']}'."
            )
    else:
        raise ValueError("Product metadata is missing from file contents.")

    # Age group validation is done explicitly for Single Year Age and Not Stated
    # The All category will have no notes information
    # Single-Year Ages may or may not have notes (depends on Group By parameters)
    # Not Stated will have "Single-Year Ages: Not Stated" in notes
    if "age_group" in notes:
        if (
            metadata["age_group"] == "Single-Year Ages"
            and "Single-Year Ages" in notes["age_group"]
        ):
            pass
        elif (
            metadata["age_group"] == "Not Stated" and "Not Stated" in notes["age_group"]
        ):
            pass
        else:
            raise ValueError(
                f"Metadata age_group: '{metadata['age_group']}' does not match file contents: '{notes['age_group']}'."
            )
    elif metadata["age_group"] in ["All", "Single-Year Ages"]:
        pass
    else:
        raise ValueError(
            f"Metadata age_group: '{metadata['age_group']}' does not match file contents."
        )

    # Sex validation is done explicitly for Female and Male
    # The All category will have no notes information
    if "sex" in notes:
        if metadata["sex"] == notes["sex"]:
            pass
        else:
            raise ValueError(
                f"Metadata sex: '{metadata['sex']}' does not match file contents: '{notes['sex']}'."
            )
    elif metadata["sex"] == "All":
        pass
    else:
        raise ValueError(
            f"Metadata sex: '{metadata['sex']}' does not match file contents."
        )

    # Hispanic validation is done explicitly excepting for All
    # The All category may have "Hispanic or Latino; Not Hispanic or Latino" in notes
    if "hispanic" in notes:
        if (
            metadata["hispanic"] == "All"
            and notes["hispanic"] == "Hispanic or Latino; Not Hispanic or Latino"
        ):
            pass
        elif metadata["hispanic"] == notes["hispanic"]:
            pass
        else:
            raise ValueError(
                f"Metadata hispanic: '{metadata['hispanic']}' does not match file contents: '{notes['hispanic']}'."
            )
    elif metadata["hispanic"] == "All":
        pass
    else:
        raise ValueError(
            f"Metadata hispanic: '{metadata['hispanic']}' does not match file contents."
        )

    # Race validation is done explicitly excepting for All
    # The All category will have no notes information
    if "race" in notes:
        if metadata["race"] == notes["race"]:
            pass
        else:
            raise ValueError(
                f"Metadata race: '{metadata['race']}' does not match file contents: '{notes['race']}'."
            )
    elif metadata["race"] == "All":
        pass
    else:
        raise ValueError(
            f"Metadata race: '{metadata['race']}' does not match file contents."
        )

    # Year validation for 5-year moving average and years
    # Build expected year string: "year-4; year-3; year-2; year-1; year"
    if "year" in notes:
        expected_years = "; ".join(
            str(int(metadata["year"]) - i) for i in reversed(range(5))
        )
        if expected_years not in notes["year"]:
            raise ValueError(
                f"Metadata year: '{metadata['year']}' (5-year moving average) does not match file contents: '{notes['year']}'."
            )
    else:
        raise ValueError("Year metadata is missing from file contents.")


def load_cdc_wonder(file_path: pathlib.Path) -> pd.DataFrame:
    """Load and transform a single CDC WONDER mortality file into a standardized DataFrame.

    This function reads a CDC WONDER mortality file, parses and validates its metadata
    from the filename, and processes the data to produce a DataFrame suitable for
    downstream analysis. It performs the following:
    - Skips files intended for 'not stated' inflation factor calculation (files with
        'Not Stated' or 'All' in key fields).
    - Filters out ages 85 and above.
    - Standardizes column names and values (e.g., race, sex, location, year).
    - For San Diego County 2022+ 5-year average files, converts deaths to annual counts
        for later merge with population data
    - Handles special cases for Hispanic/Not Hispanic and 'All' race combinations.

    Args:
        file_path (pathlib.Path): Path to the CDC WONDER mortality file.

    Returns:
        pd.DataFrame: Processed DataFrame with columns standardized and filtered for
            ages 0-84. Returns an empty DataFrame if the file is meant for 'not stated'
            inflation factor calculation.
    """

    # Get metadata dict for column assignment
    metadata = parse_filename(file_path)

    # Files with fields that are "Not Stated" or "All" across all fields are skipped
    # These files are meant for calculating inflation factors for "Not Stated" values
    if (
        (metadata["age_group"] == "Not Stated")
        | (metadata["hispanic"] == "Not Stated")
        | (
            (metadata["sex"] == "All")
            & (metadata["race"] == "All")
            & (metadata["hispanic"] == "All")
        )
    ):
        raise ValueError(
            "Files used in not stated calculation should be omitted when loading in the "
            "CDC WONDER mortality data as they have been dealt with separately."
        )

    # Ages to be excluded from dataset
    excluding_sya = [str(age) for age in range(85, 101)]

    df = (
        pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            usecols=lambda col: col
            in [
                "Single-Year Ages Code",
                "Sex Code",
                "Hispanic Origin",
                "Year",
                "Deaths",
                "Population",
                "Race",
                "Single Race 6",
                "Notes",
            ],
        )
        .pipe(lambda x: (x.loc[: x[x["Notes"] == "---"].index.min() - 1]))
        .drop(columns=["Notes"])
        .rename(
            columns={
                "Single-Year Ages Code": "age",
                "Sex Code": "sex",
                "Hispanic Origin": "hispanic origin",
                "Year": "year",
                "Deaths": "deaths",
                "Population": "pop",
                "Race": "race",
                "Single Race 6": "race",
            }
        )
        .assign(
            race=lambda x: x["race"] if "race" in x.columns else "Hispanic",
            location=metadata["location"],
            year=pd.to_numeric(metadata["year"], errors="coerce"),
            product=metadata["product"],
            # Convert 2022+ San Diego County 5-year average deaths to annual deaths
            # Population for 2022+ county level is suppressed and will be replaced
            # with yearly CCM population estimates which require annual death counts to
            # calculate rates
            deaths=lambda x: pd.to_numeric(x["deaths"], errors="coerce")
            / (
                5
                if int(metadata["year"]) >= 2022
                and metadata["location"] == "San Diego County"
                else 1
            ),
        )
        .loc[lambda x: (~x["age"].isin(excluding_sya))]
        .replace(
            {
                "Asian": "Asian alone",
                "Asian or Pacific Islander": "Asian alone",
                "Black or African American": "Black or African American alone",
                "American Indian or Alaska Native": "American Indian or Alaska Native alone",
                "More than one race": "Two or More Races",
                "White": "White alone",
                "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Islander alone",
            }
        )
        .pipe(
            lambda x: (
                x.assign(pop=pd.to_numeric(x["pop"], errors="coerce"))
                if "pop" in x.columns
                else x
            )
        )
        .assign(age=lambda x: pd.to_numeric(x["age"], errors="coerce"))
        .dropna(subset=["age"])
    )

    # Files with race="All" AND hispanic="Hispanic or Latino" represent Hispanic data
    if (
        (metadata["race"] == "All")
        and (metadata["hispanic"] == "Hispanic or Latino")
        and (metadata["sex"] != "All")
    ):
        df["race"] = "Hispanic"
    # Files with race="All" AND hispanic="Not Hispanic or Latino" will be marked as "All"
    # and later duplicated into NHPI and MOR (races with insufficient data)
    elif (
        (metadata["race"] == "All")
        and (metadata["hispanic"] == "Not Hispanic or Latino")
        and (metadata["sex"] != "All")
    ):
        df["race"] = "All"

    # Duplicate 'All' race rows into NHPI and MOR, keep other races
    all_races = df[df["race"] == "All"]
    result = pd.concat(
        [
            df[df["race"] != "All"],
            all_races.assign(race="Native Hawaiian or Other Pacific Islander alone"),
            all_races.assign(race="Two or More Races"),
        ],
        ignore_index=True,
    )

    return result


def parse_not_stated(year: int) -> pd.DataFrame:
    """Calculate inflation factor for "not stated" deaths for a specific year.

    The CDC WONDER contains multiple rows marked as "Not Stated"/"NS". This function
    locates the number of not stated deaths versus stated deaths for a specific year,
    separated by geography and sex, then calculates an inflation factor.

    Only processes files with 2 or more "ALL" values in the metadata (files meant for
    not stated calculation) and matching the specified year.

    Args:
        year (int): The year to calculate inflation factors for.

    Returns:
        pd.DataFrame: A DataFrame with location, sex, and inflation factor for the
            specified year.
    """

    ns, stated = [], []

    # Look only in the specific year folder
    year_folder = pathlib.Path(f"data/deaths/{year}")

    for file_path in year_folder.glob("*"):
        if file_path.is_file():
            try:
                # Parse metadata from filename
                metadata = parse_filename(file_path)

                # Only process files related to "Not Stated" calculation
                # These are files with age_group="Not Stated" OR hispanic="Not Stated"
                # OR files with all demographics set to "All"
                if not (
                    (metadata["age_group"] == "Not Stated")
                    | (metadata["hispanic"] == "Not Stated")
                    | (
                        (metadata["sex"] == "All")
                        & (metadata["race"] == "All")
                        & (metadata["hispanic"] == "All")
                    )
                ):
                    continue

                # Validate not stated files
                validate_file(file_path)

                # Read in data
                df = (
                    pd.read_csv(file_path, sep=None, engine="python")
                    .rename(columns=str.lower)
                    .loc[:, ["sex", "deaths"]]
                    .dropna()
                    .assign(
                        location=metadata["location"],
                        sex=lambda x: x["sex"].replace({"Male": "M", "Female": "F"}),
                        deaths=lambda x: pd.to_numeric(
                            x["deaths"].replace({"Suppressed": "0"}), errors="coerce"
                        ),
                    )
                )

                # Separate data by status
                if (metadata["age_group"] == "Not Stated") | (
                    metadata["hispanic"] == "Not Stated"
                ):
                    ns.append(df)
                else:
                    stated.append(df)

            except (ValueError, KeyError, IndexError):
                # Skip files that don't match expected format
                continue

    # Concatenate and aggregate
    ns = (
        pd.concat(ns, ignore_index=True)
        .groupby(["location", "sex"], as_index=False)["deaths"]
        .sum()
    )
    stated = (
        pd.concat(stated, ignore_index=True)
        .groupby(["location", "sex"], as_index=False)["deaths"]
        .sum()
    )

    # Merge and create inflation factor
    result = pd.merge(
        ns,
        stated,
        on=["location", "sex"],
        suffixes=("_not_stated", "_stated"),
    ).assign(
        inflation_factor=lambda x: 1 + (x["deaths_not_stated"] / x["deaths_stated"])
    )[
        ["location", "sex", "inflation_factor"]
    ]

    return result


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

    Args:
        pop_df (pd.DataFrame): Population dataframe from CCM for 2018+ product
            population estimates.
        year (int): The year to load data for.

    Returns:
        pd.DataFrame: A single DataFrame for the specified year with data for
        ages 0-99 from the CDC.
    """

    all_data = []

    # Look in the specific year folder
    year_folder = pathlib.Path(f"data/deaths/{year}")
    if not year_folder.exists():
        raise ValueError(f"Year folder not found: {year_folder}")

    # Calculate inflation factor for this year
    inflation_factor = parse_not_stated(year)

    for file_path in year_folder.glob("*"):
        if file_path.is_file():
            meta = parse_filename(file_path)

            # Skip files used in not stated calculation
            if (
                (meta["age_group"] == "Not Stated")
                | (meta["hispanic"] == "Not Stated")
                | (
                    (meta["sex"] == "All")
                    & (meta["race"] == "All")
                    & (meta["hispanic"] == "All")
                )
            ):
                continue

            validate_file(file_path)

            # Use unified load_cdc_wonder function
            df = load_cdc_wonder(file_path)
            if not df.empty:
                # For the 2018+ product, merge SD County deaths with CCM population
                if (
                    meta["product"] == "2018+"
                    and meta["location"] == "San Diego County"
                    and pop_df is not None
                ):
                    df = df.merge(
                        pop_df.assign(year=year)[["year", "age", "sex", "race", "pop"]],
                        on=["year", "age", "sex", "race"],
                        how="left",
                    )

                # Merge with inflation factors and inflate deaths/rates
                df = (
                    pd.merge(df, inflation_factor, on=["location", "sex"])
                    .assign(
                        deaths=lambda x: x["deaths"] * x["inflation_factor"],
                        rates=lambda x: np.where(
                            x["deaths"].isnull(), np.nan, x["deaths"] / x["pop"]
                        ),
                    )
                    .drop(columns=["inflation_factor"])
                )

                all_data.append(df)

    # Combine all data
    all_data = pd.concat(all_data, ignore_index=True)

    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        all_data.pivot_table(
            index=["year", "age", "race", "sex", "hispanic origin"],
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

    # Geography Hierarchy for rates: County > State > National
    pivoted["rates"] = np.where(
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
            columns 'age', 'rates', 'sex', 'race/ethnicity', and 'year'.
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
    required_cols = ["age", "rates", "sex", "race/ethnicity", "year"]
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
        for race in df["race/ethnicity"].unique():
            for year in df["year"].unique():
                mask = (
                    (df["sex"] == sex)
                    & (df["race/ethnicity"] == race)
                    & (df["year"] == year)
                )

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


def get_death_rates(
    yr: int,
    launch_yr: int,
    ss_life_tbl: pd.DataFrame,
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

    For ages >= 85 the Social Security Actuarial Life Table is used,
    substituting the 2019 dataset for base years 2020 and 2021 due to the
    outsize impact of COVID-19 on geriatric death rates.

    The CDC WONDER dataset for 2021 is unavailable, so 2020 data is used
    as a substitute for year 2021. Smoothing is applied ONLY to CDC data (ages 0-84)
    to preserve the race-agnostic nature of the SS life table at ages 85+.

    Args:
        yr: Increment year
        launch_yr: Launch year
        ss_life_tbl (pd.DataFrame): Social Security Actuarial Life Table from
            death_rates.load_ss_life_tbl
        pop_df (pd.DataFrame): Population data for the year
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.

    Returns:
        pd.DataFrame: Death rates broken down by race, sex, and single year
            of age
    """
    # Death rates calculated from year up to the launch year
    if yr <= launch_yr:
        # For the Social Security Actuarial Life Table dataset
        # If current year is not available grab the most recent available year
        if yr not in ss_life_tbl["year"].unique():
            ss_yr = ss_life_tbl["year"][ss_life_tbl["year"] <= yr].max()
            logger.warning(
                "Social Security Actuarial Life Table dataset unavailable for: "
                + str(yr)
                + " Default to most recent dataset: "
                + str(ss_yr)
            )
        else:
            ss_yr = yr

        # Social Security Actuarial Life Table dataset
        # Years 2020 and 2021 not used due to COVID-19 impact on geriatric death rates
        # Default to 2019 data
        if ss_yr in [2020, 2021]:
            ss_yr = 2019
            logger.warning(
                "Social Security Actuarial Life Table dataset not used for 2020/2021. "
                "Defaulting to 2019 data."
            )

        # Load and process CDC WONDER mortality data
        # Determine which year's data to use (2021 uses 2020 data)
        cdc_yr = 2020 if yr == 2021 else yr
        if yr == 2021:
            logger.warning("CDC WONDER data unavailable for 2021. Using 2020 data.")

        # Load mortality data for this specific year
        cdc_rates = load_local_files(pop_df=pop_df, year=cdc_yr)[
            ["race", "sex", "age", "rates"]
        ]

        # Get unique race categories from CDC data
        race_categories = cdc_rates["race"].unique()

        # Filter Social Security Actuarial Life Table to chosen year and ages >= 85
        ss_rates = ss_life_tbl.loc[
            (ss_life_tbl["year"] == ss_yr) & (ss_life_tbl["age"] >= 85)
        ][["age", "sex", "rate"]].rename(columns={"rate": "rates"})

        # Expand SS rates to include all race categories
        # (SS life table doesn't have race breakdown, so apply same rates to all races)
        ss_expanded = []
        for race in race_categories:
            ss_race = ss_rates.copy()
            ss_race["race"] = race
            ss_expanded.append(ss_race)

        ss_rates_expanded = pd.concat(ss_expanded, ignore_index=True)

        # Apply smoothing to CDC data ONLY (ages 0-84)
        if smooth_s is not None and smooth_k is not None:
            # Prepare CDC DataFrame for smooth_rates function
            cdc_for_smoothing = cdc_rates.copy()
            cdc_for_smoothing["year"] = cdc_yr
            cdc_for_smoothing = cdc_for_smoothing.rename(
                columns={"race": "race/ethnicity"}
            )

            # Apply smoothing
            cdc_smoothed = smooth_rates(cdc_for_smoothing, s=smooth_s, k=smooth_k)

            # Update the existing rates column with smoothed values
            cdc_rates["rates"] = cdc_smoothed["rates"].values

        # Combine CDC rates (ages 0-84) with SS rates (ages 85+)
        rates = pd.concat([cdc_rates, ss_rates_expanded], ignore_index=True).rename(
            columns={"rates": "rate_death"}
        )

        return rates[["race", "sex", "age", "rate_death"]]

    # Death rates are not calculated after the launch year
    else:
        raise ValueError("Death rates not calculated past launch year")


def load_ss_life_tbl(file_path: str) -> pd.DataFrame:
    """Load the Social Security Actuarial Life Table.

    Load the Social Security Actuarial Life Table replacing age records >= 110
    with the weighted average of the crude death rate for all age records
    >= 110 within the given year.

    Args:
        file_path: Path to Social Security Actuarial Life Table file

    Returns:
        pd.DataFrame: The Social Security Actuarial Life Table
    """
    # Load the Social Security Actuarial Life Table
    df = pd.read_csv(
        file_path,
        usecols=[
            "Year",
            "Exact age",
            "Male Death Probability",
            "Male Number of lives",
            "Female Death Probability",
            "Female Number of lives",
        ],
        dtype={
            "Year": int,
            "Exact age": int,
            "Male Death Probability": float,
            "Male Number of lives": int,
            "Female Death Probability": float,
            "Female Number of lives": int,
        },
    ).rename(
        columns={
            "Year": "year",
            "Exact age": "age",
            "Male Death Probability": "rate-M",
            "Male Number of lives": "lives-M",
            "Female Death Probability": "rate-F",
            "Female Number of lives": "lives-F",
        }
    )

    # Calculate weighted crude death rate for ages >= 110
    # Assign this death rate for ages 110+
    weighted_df = df[df["age"] >= 110].copy()
    weighted_df["weighted-M"] = weighted_df["rate-M"] * weighted_df["lives-M"]
    weighted_df["weighted-F"] = weighted_df["rate-F"] * weighted_df["lives-F"]

    weighted_df = (
        weighted_df.groupby("year")[
            [
                "lives-M",
                "weighted-M",
                "lives-F",
                "weighted-F",
            ]
        ]
        .sum()
        .reset_index()
    )

    weighted_df["rate-M"] = weighted_df["weighted-M"] / weighted_df["lives-M"]
    weighted_df["rate-F"] = weighted_df["weighted-F"] / weighted_df["lives-F"]
    weighted_df["age"] = 110

    # Replace ages >= 110 with the weighted crude death rate
    df = pd.concat(
        [
            df[df["age"] < 110][["year", "age", "rate-M", "rate-F"]],
            weighted_df[["year", "age", "rate-M", "rate-F"]],
        ],
        ignore_index=True,
    )

    # Transform DataFrame structure to long-format
    df = pd.wide_to_long(
        df=df,
        stubnames="rate",
        i=[
            "year",
            "age",
        ],
        j="sex",
        sep="-",
        suffix=r"\w+",
    ).reset_index()

    return df
