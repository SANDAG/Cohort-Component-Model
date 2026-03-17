import logging
import pathlib
import scipy
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Module-level cache for batch loading mortality data across function calls
_MORTALITY_CACHE = {}


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
                "HIS": "Hispanic",
                "NHPI": "Native Hawaiian or Other Pacific Islander",
                "WH": "White",
                "ALL": "All",
                "NA": "Not Available",
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

    # Race validation is done explicitly excepting for All and Hispanic
    # The All and Hispanic category will have no notes information
    if "race" in notes:
        if metadata["race"] == notes["race"]:
            pass
        else:
            raise ValueError(
                f"Metadata race: '{metadata['race']}' does not match file contents: '{notes['race']}'."
            )
    elif metadata["race"] in ["All", "Hispanic"]:
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
    """Load and transform a single CDC WONDER file into a DataFrame.

    Filter for ages 84 and under. Populate location and year for each row. For
    1999-2020 CDC, assign "Hispanic" race to all rows missing a race. For 2018-2023 CDC,
    collapse multiple race columns into one titled "race". Assign "race" for races with
    no race column.

    Files with 2 or more "ALL" values are skipped as they are meant for not stated
    inflation factor calculation.

    Args:
        file_path (pathlib.Path): The file path.

    Returns:
        pd.DataFrame: A processed dataframe for the CDC product, or empty DataFrame
            if file should be skipped.
    """

    # Get metadata dict for column assignment
    metadata = parse_filename(file_path)

    # Skip files with 2+ "ALL" values (meant for not stated calculation)
    all_count = sum(1 for value in metadata.values() if value == "ALL")
    if all_count >= 2:
        return pd.DataFrame()

    # Ages to be excluded from dataset
    excluding_sya = [str(age) for age in range(85, 101)]

    required_columns_1999 = [
        "Single-Year Ages Code",
        "Sex Code",
        "Hispanic Origin",
        "Race",
        "Year",
        "Deaths",
        "Population",
    ]

    column_map_1999 = {
        "Single-Year Ages Code": "age",
        "Sex Code": "sex",
        "Hispanic Origin": "hispanic origin",
        "Race": "race",
        "Year": "year",
        "Deaths": "deaths",
        "Population": "pop",
        "Location": "location",
    }

    required_columns_2018 = [
        "Single-Year Ages Code",
        "Sex Code",
        "Hispanic Origin",
        "Single Race 6",
        "Year",
        "Deaths",
        "Population",
    ]

    column_map_2018 = {
        "Single-Year Ages Code": "age",
        "Sex Code": "sex",
        "Hispanic Origin": "hispanic origin",
        "Year": "year",
        "Single Race 6": "race",
        "Deaths": "deaths",
        "Population": "pop",
        "Location": "location",
    }

    df = pd.read_csv(file_path, sep=None, engine="python").pipe(
        lambda x: (x.loc[: x[x["Notes"] == "---"].index.min() - 1])
    )

    # Determine which format based on column presence
    if "Single Race 6" not in df.columns:
        # 1999-2020 format
        required_columns = required_columns_1999
        column_map = column_map_1999
    elif "Single Race 6" in df.columns:
        # 2018-2023 format
        required_columns = required_columns_2018
        column_map = column_map_2018

    df = (
        df.loc[:, lambda x: [col for col in required_columns if col in x.columns]]
        .rename(columns=column_map, errors="ignore")
        .assign(
            race=lambda x: x["race"] if "race" in x.columns else "Hispanic",
            location=metadata["location"],
            year=pd.to_numeric(metadata["year"], errors="coerce"),
            product=metadata["product"],
            deaths=lambda x: pd.to_numeric(x["deaths"], errors="coerce"),
        )
        .assign(
            deaths=lambda x: np.where(
                (x["year"] >= 2022) & (x["location"] == "San Diego County"),
                x["deaths"] / 5,
                x["deaths"],
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
    )

    # Set up dtypes for population where it exists
    if "pop" in df.columns:
        df = df.assign(pop=lambda x: pd.to_numeric(x["pop"], errors="coerce"))

    # Mark files with race="ALL" for later duplication (after all math/splining)
    # This is more efficient than duplicating before processing
    if (metadata["race"] == "ALL") and (metadata["sex"] != "ALL"):
        df["race"] = "ALL_RACES"

    return pd.DataFrame(df)


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

    # Comb through data files for the specific year
    for file_path in pathlib.Path("data/deaths").rglob("*"):
        if file_path.is_file():
            try:
                # Parse metadata from filename
                metadata = parse_filename(file_path)

                # Only process files with 2+ "ALL" values and matching year
                all_count = sum(1 for value in metadata.values() if value == "ALL")
                if all_count < 2 or int(metadata["year"]) != year:
                    continue

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

                # Separate data by status (check if age_group is "SYA NS")
                if metadata["age_group"] == "SYA NS":
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


def inflate_deaths(df: pd.DataFrame) -> pd.DataFrame:
    """Inflate death counts based on the proportion of deaths labeled as "Not Stated".

    The rows with "Not Stated" or "NS" have associated death counts but no population
    counts, making them unattributable to a specific demographic.

    To address this, the function:
    - Inflates the attributable deaths by this proportion
    - Recalculates rates based on the inflated death counts

    Args:
        df (pd.DataFrame): A geography-specific DataFrame containing mortality data.

    Returns:
        pd.DataFrame: A processed DataFrame with adjusted death counts, rates, and no
            "Not Stated" demographic entries.
    """

    # Get the year from the dataframe (assumes single year per call)
    year = int(df["year"].iloc[0])
    data = parse_not_stated(year)

    # Create a filtered DataFrame for "Stated" responses
    stated_df = df.loc[
        lambda x: (x["hispanic origin"] != "Not Stated") & (x["age"] != "NS")
    ]

    results = (
        pd.merge(stated_df, data, on=["location", "sex"])
        .assign(
            deaths=lambda x: x["deaths"] * x["inflation_factor"],
            rates=lambda x: np.where(
                x["deaths"].isnull(), np.nan, x["deaths"] / x["pop"]
            ),
        )
        .drop(columns=["inflation_factor"])
    )

    return results


def deaths_recode(deaths: int, pop: int) -> float:
    """Recode WONDER deaths 0 and "Suppressed" values.

    This function is used as the final methodology for substituting missing rates where
    deaths are imputed using the following logic.

    Args:
        deaths (int): The total number of deaths.
        pop (int): The total population.

    Returns:
        float: The recoded number of deaths.
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


def rate_substitution(row: pd.Series, age_max: int, age_min: int) -> tuple[float, str]:
    """Determine mortality rate for a given row based on data availability.

    Mortality rates that are missing from the county level dataset are substituted in
    the following order:

    1) State rate
    2) National rate
    3) Average rate
        - The average of the county rates from ages before and after the target age
        - ex. target age is 4 therefore take the average rate of age 3 and 5
    4) Previous rate
        - The rate of the previous age from the target age in the county dataset
        - ex. target age is 4 therefore take the rate of the previous age (3)
    5) Next rate
        - The rate of the next age from the target age in the county dataset
        - ex. target age is 4 therefore take the rate of the next age (5)
    6) Imputation
        - Impute using deaths_recode with NATIONAL data

    For each substitution, a corresponding label defining which methodology/dataset was
    used for the substitution will be documented as well.

    Args:
        row (pd.series): A row of data containing rate data.
        age_max (int): The max age in the dataset.
        age_min (int): The minimum age in the dataset.

    Returns:
        tuple[float, str]: The selected rate substitution, and the corresponding
            substitution label.
    """

    if pd.notna(row["rates_county"]) and row["rates_county"] != 0:
        return row["rates_county"], "San Diego County Data"
    elif pd.notna(row["rates_state"]) and row["rates_state"] != 0:
        return row["rates_state"], "California Data Substituted"
    elif pd.notna(row["rates_national"]) and row["rates_national"] != 0:
        return row["rates_national"], "United States Data Substituted"
    elif pd.notna(row["rate_avg"]) and row["rate_avg"] != 0:
        return row["rate_avg"], "Average Rate Substituted"
    elif pd.notna(row["rate_next"]) and row["rate_next"] != 0 and row["age"] != age_max:
        return row["rate_next"], "Next Rate Substituted"
    elif pd.notna(row["rate_prev"]) and row["rate_prev"] != 0 and row["age"] != age_min:
        return row["rate_prev"], "Previous Rate Substituted"
    else:
        return row["rate_imputed"], "Imputation (National Data)"


def merge_geographies(
    county: pd.DataFrame, state: pd.DataFrame, national: pd.DataFrame
) -> pd.DataFrame:
    """Merge and impute mortality rates using hierarchical geographic sources.

    This function merges mortality data from county, state, and national levels to
    produce a unified DataFrame in which missing county-level rates are substituted
    using the rate_substitution and track_changes functions.

    Args:
        county (pd.DataFrame): A DataFrame containing mortality data for San Diego
            County.
        state (pd.DataFrame): A DataFrame containing mortality data for the state of
            California.
        national (pd.DataFrame): A DataFrame containing mortality data for the United
            States.

    Returns:
        pd.DataFrame: A single DataFrame primarily based on county data, with missing
            rates substituted using state and national data.
    """

    # Filter out any rows with NaN age values
    county = county.dropna(subset=["age"])
    state = state.dropna(subset=["age"])
    national = national.dropna(subset=["age"])

    age_min = county["age"].min()
    age_max = county["age"].max()

    # Merge county with state and national data
    county_merged = (
        county.merge(
            state[["year", "age", "race", "sex", "hispanic origin", "rates"]],
            on=["year", "age", "race", "sex", "hispanic origin"],
            how="left",
            suffixes=("", "_state"),
        )
        .merge(
            national[
                [
                    "year",
                    "age",
                    "race",
                    "sex",
                    "hispanic origin",
                    "rates",
                    "deaths",
                    "pop",
                ]
            ],
            on=["year", "age", "race", "sex", "hispanic origin"],
            how="left",
            suffixes=("", "_national"),
        )
        .rename(
            columns={
                "rates": "rates_county",
                "deaths": "deaths_county",
                "pop": "pop_county",
            }
        )
        .assign(
            year=lambda x: x["year"].astype(int),
        )
        .sort_values(["sex", "hispanic origin", "race", "year", "age"])
        .assign(
            rate_prev=lambda x: x["rates_county"].shift(1),
            rate_next=lambda x: x["rates_county"].shift(-1),
            rate_avg=lambda x: np.where(
                pd.notna(x["rate_next"]) & pd.notna(x["rate_prev"]),
                x[["rate_prev", "rate_next"]].mean(axis=1),
                np.nan,
            ),
            rate_imputed=lambda x: x.apply(
                lambda row: deaths_recode(row["deaths_national"], row["pop_national"])
                / row["pop_national"],
                axis=1,
            ),
        )
        .pipe(
            lambda x: x.assign(
                rates=x.apply(
                    lambda row: rate_substitution(row, age_min, age_max)[0], axis=1
                ),
                tracked_changes=x.apply(
                    lambda row: rate_substitution(row, age_min, age_max)[1], axis=1
                ),
            )
        )
        .drop(
            columns=[
                "rates_county",
                "rates_state",
                "rates_national",
                "product",
                "hispanic origin",
                "deaths_county",
                "deaths_national",
                "pop_county",
                "pop_national",
                "location",
                "rate_prev",
                "rate_next",
                "rate_avg",
                "rate_imputed",
            ]
        )
    )

    return county_merged


def load_local_files(pop_df: pd.DataFrame, years: int | list[int]) -> pd.DataFrame:
    """Load files from a directory for specific year(s) and combine them by product.

    Args:
        pop_df (pd.DataFrame): Population dataframe from CCM for 2018-2023
            product population estimates.
        years (int | list[int]): A single year or list of years to load data for.

    Returns:
        pd.DataFrame: A single DataFrame for the specified year(s) with data for
        ages 0-99 from the CDC.
    """

    # Normalize years to a set
    if isinstance(years, int):
        target_years = {years}
    else:
        target_years = set(years)

    data_by_product = {
        "1999-2020": {"San Diego County": [], "California": [], "US": []},
        "2018-2023": {"San Diego County": [], "California": [], "US": []},
    }

    for file_path in pathlib.Path("data/deaths").rglob("*"):
        if file_path.is_file():
            meta = parse_filename(file_path)

            # Only process files for the specified year(s)
            if int(meta["year"]) not in target_years:
                continue

            validate_file_name(file_path)

            product = meta["product"]

            # Use unified load_cdc_wonder function
            df = load_cdc_wonder(file_path)
            if not df.empty:
                location = df["location"].iloc[0]

                # Convert age to numeric and ensure consistent types
                df["age"] = pd.to_numeric(df["age"], errors="coerce")
                df = df.dropna(subset=["age"])
                df = df.astype({"age": int, "year": int, "sex": str, "race": str})

                # For 2018-2023 San Diego County, merge with CCM population
                if (
                    product == "2018-2023"
                    and location == "San Diego County"
                    and pop_df is not None
                ):
                    pop_df_with_year = pop_df.copy()
                    pop_df_with_year["year"] = int(meta["year"])
                    pop_df_with_year = pop_df_with_year.astype(
                        {"age": int, "sex": str, "race": str}
                    )

                    df = df.merge(
                        pop_df_with_year[["year", "age", "sex", "race", "pop"]],
                        on=["year", "age", "sex", "race"],
                        how="left",
                    )

                # Inflate deaths for both products
                df = inflate_deaths(df)

                data_by_product[product][location].append(df)

    all_products = []

    for product, locations in data_by_product.items():
        county_dfs = locations["San Diego County"]
        state_dfs = locations["California"]
        national_dfs = locations["US"]

        if not county_dfs or not state_dfs or not national_dfs:
            continue

        county = pd.concat(county_dfs, ignore_index=True)
        state = pd.concat(state_dfs, ignore_index=True)
        national = pd.concat(national_dfs, ignore_index=True)
        substituted_df = merge_geographies(county, state, national)

        all_products.append(substituted_df)

    # Finalize combined dataset
    df = (
        pd.concat(all_products, ignore_index=True)
        .sort_values(by=["sex", "race", "year", "age"])
        .loc[lambda x: x["age"] <= 99]
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


def duplicate_all_races(df: pd.DataFrame) -> pd.DataFrame:
    """Duplicate rows marked as 'ALL_RACES' into NHPI and MOR race categories.

    This should be called after all mathematical operations (smoothing, etc.) are
    complete to avoid doing expensive calculations twice.

    Args:
        df (pd.DataFrame): DataFrame potentially containing 'ALL_RACES' rows.

    Returns:
        pd.DataFrame: DataFrame with 'ALL_RACES' rows duplicated and renamed to
            'Native Hawaiian or Other Pacific Islander alone' and 'Two or More Races'.
    """
    # Check if there are any ALL_RACES rows
    if "ALL_RACES" not in df["race"].values:
        return df

    # Split into ALL_RACES and non-ALL_RACES
    all_races_df = df[df["race"] == "ALL_RACES"].copy()
    other_df = df[df["race"] != "ALL_RACES"].copy()

    # Duplicate ALL_RACES into NHPI and MOR
    nhpi_df = all_races_df.copy()
    nhpi_df["race"] = "Native Hawaiian or Other Pacific Islander alone"

    mor_df = all_races_df.copy()
    mor_df["race"] = "Two or More Races"

    # Concatenate all back together
    result = pd.concat([other_df, nhpi_df, mor_df], ignore_index=True)

    return result


def get_death_rates(
    yr: int,
    launch_yr: int,
    ss_life_tbl: pd.DataFrame,
    pop_df: pd.DataFrame,
    smooth_s: int = 5,
    smooth_k: int = 2,
    base_yr: int = None,
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

    This function uses a module-level cache to batch load all needed years
    (from base_yr to launch_yr) in a single directory scan on the first invocation,
    then retrieves specific years from the cache on subsequent calls.

    Args:
        yr: Increment year
        launch_yr: Launch year
        ss_life_tbl (pd.DataFrame): Social Security Actuarial Life Table from
            death_rates.load_ss_life_tbl
        pop_df (pd.DataFrame): Population data for the year
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.
        base_yr (int, optional): Base year for batch loading. If provided, loads all
            years from base_yr to launch_yr on first call. If omitted, defaults to yr.

    Returns:
        pd.DataFrame: Death rates broken down by race, sex, and single year
            of age
    """
    # Death rates calculated from base year up to the launch year
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

        # Batch load on first call (cache key is launch_yr to allow different horizons)
        cache_key = f"launch_{launch_yr}"
        if cache_key not in _MORTALITY_CACHE:
            # Determine all years needed (base_yr to launch_yr, map 2021 to 2020)
            start_year = base_yr if base_yr is not None else yr
            needed_years = set(range(start_year, launch_yr + 1))
            if 2021 in needed_years:
                needed_years.add(2020)  # 2021 uses 2020 data

            logger.warning(
                "Batch loading mortality data for years: " + str(sorted(needed_years))
            )
            _MORTALITY_CACHE[cache_key] = load_local_files(
                pop_df=pop_df, years=list(needed_years)
            )

        # Retrieve data from cache for the specific year
        mortality_df = (
            _MORTALITY_CACHE[cache_key]
            .loc[_MORTALITY_CACHE[cache_key]["year"] == cdc_yr]
            .copy()
        )

        # Filter to ages < 85, keep only necessary columns
        cdc_rates = mortality_df.loc[mortality_df["age"] < 85][
            ["race", "sex", "age", "rates"]
        ].rename(columns={"rates": "rate_death"})

        # Get unique race categories from CDC data
        race_categories = cdc_rates["race"].unique()

        # Filter Social Security Actuarial Life Table to chosen year and ages >= 85
        ss_rates = ss_life_tbl.loc[
            (ss_life_tbl["year"] == ss_yr) & (ss_life_tbl["age"] >= 85)
        ][["age", "sex", "rate"]].rename(columns={"rate": "rate_death"})

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
                columns={"race": "race/ethnicity", "rate_death": "rates"}
            )

            # Apply smoothing
            cdc_smoothed = smooth_rates(cdc_for_smoothing, s=smooth_s, k=smooth_k)

            # Update CDC rates with smoothed values
            cdc_rates["rate_death"] = cdc_smoothed["rates"].values

        # Combine smoothed CDC rates (ages 0-84) with unsmoothed SS rates (ages 85+)
        rates = pd.concat([cdc_rates, ss_rates_expanded], ignore_index=True)

        # Duplicate ALL_RACES rows into NHPI and MOR
        rates = duplicate_all_races(rates)

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
