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
            "map": {
                "SYA": "Single-Year Ages",
                "TYA": "Ten-Year Ages",
                "NS": "Not Stated",
                "ALL": "All",
            },
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
            elif line.startswith("Ten-Year Age Groups"):
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

    # Age group validation is done explicitly for Single Year Age, Ten Year Age, and Not Stated
    # The All category will have no notes information
    # Single-Year Ages may or may not have notes (depends on Group By parameters)
    # Ten-Year Ages will have "Ten-Year Age Groups" in notes
    # Not Stated will have "Single-Year Ages: Not Stated" in notes
    if "age_group" in notes:
        if (
            metadata["age_group"] == "Single-Year Ages"
            and "Single-Year Ages" in notes["age_group"]
        ):
            pass
        elif (
            metadata["age_group"] == "Ten-Year Ages"
            and "Ten-Year Age Groups" in notes["age_group"]
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
    elif metadata["age_group"] in ["All", "Single-Year Ages", "Ten-Year Ages"]:
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
    - For SYA (Single-Year Ages) files: Filters out ages 85 and above.
    - For TYA (Ten-Year Ages) files: Filters for only the 85+ age group.
    - Standardizes column names and values (e.g., race, sex, location, year).
    - For San Diego County 2022+ 5-year average files, converts deaths to annual counts
        for later merge with population data
    - Handles special cases for Hispanic/Not Hispanic and 'All' race combinations.

    Args:
        file_path (pathlib.Path): Path to the CDC WONDER mortality file.

    Returns:
        pd.DataFrame: Processed DataFrame with columns standardized. For SYA files,
            returns ages 0-84. For TYA files, returns only 85+ group. Returns an empty
            DataFrame if the file is meant for 'not stated'
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

    # Determine if this is SYA or TYA file
    is_tya = metadata["age_group"] == "Ten-Year Ages"

    # Define age column name based on file type
    age_col = "Ten-Year Age Groups Code" if is_tya else "Single-Year Ages Code"

    # Ages to be excluded from dataset (only for SYA files)
    excluding_sya = [str(age) for age in range(85, 101)]

    df = (
        pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            usecols=lambda col: col
            in [
                "Single-Year Ages Code",
                "Ten-Year Age Groups Code",
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
                age_col: "age",
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
            # Determine race: Hispanic if hispanic origin is HIS, otherwise use race from CSV or metadata
            # For TYA files, race column doesn't exist so we use metadata
            race=lambda x: (
                "Hispanic"
                if metadata["hispanic"] == "Hispanic or Latino"
                else (x["race"] if "race" in x.columns else metadata["race"])
            ),
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
    )

    # Filter ages based on file type
    if is_tya:
        # For TYA files, keep only 85+ group and convert to age 85
        df = df.loc[lambda x: x["age"] == "85+"].assign(
            age=lambda x: x["age"].replace({"85+": "85"})
        )
    else:
        # For SYA files, exclude ages 85+
        df = df.loc[lambda x: (~x["age"].isin(excluding_sya))]

    df = (
        df.replace(
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
    # Only needed for 2020 and before
    elif (
        (metadata["race"] == "All")
        and (metadata["hispanic"] == "Not Hispanic or Latino")
        and (metadata["sex"] != "All")
        and (int(metadata["year"]) <= 2020)
    ):
        df["race"] = "All"

    # Duplicate 'All' race rows into NHPI and MOR for years <= 2020 only
    # For years >= 2022, actual race-specific files with sufficient data exist
    if int(metadata["year"]) <= 2020:
        all_races = df[df["race"] == "All"]
        result = pd.concat(
            [
                df[df["race"] != "All"],
                all_races.assign(
                    race="Native Hawaiian or Other Pacific Islander alone"
                ),
                all_races.assign(race="Two or More Races"),
            ],
            ignore_index=True,
        )
    else:
        result = df

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

    This function processes both Single-Year Age (SYA) files for ages 0-84 and
    Ten-Year Age (TYA) files for age 85 (85-99).

    Args:
        pop_df (pd.DataFrame): Population dataframe from CCM for 2018+ product
            population estimates.
        year (int): The year to load data for.

    Returns:
        pd.DataFrame: A single DataFrame for ages 0-85 with mortality rates.
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

                    # For TYA files (age 85 = ages 85-99), sum population across age range
                    if meta["age_group"] == "Ten-Year Ages":
                        pop_85plus = (
                            pop_df.loc[pop_df["age"].between(85, 99)][
                                ["sex", "race", "pop"]
                            ]
                            .groupby(["sex", "race"], as_index=False)["pop"]
                            .sum()
                            .assign(age=85)
                        )
                        df = df.merge(
                            pop_85plus,
                            on=["age", "sex", "race"],
                            how="left",
                        )
                    else:
                        # For SYA files, use direct age match
                        df = df.merge(
                            pop_df[["age", "sex", "race", "pop"]],
                            on=["age", "sex", "race"],
                            how="left",
                        )

                # Combine both SYA and TYA data
                all_data.append(df)

    # Combine all data (SYA ages 0-84 and TYA age 85)
    if not all_data:
        raise ValueError(f"No data found for year {year}")

    combined = pd.concat(all_data, ignore_index=True)

    # Inflate deaths and calculate rates for all ages
    combined = (
        pd.merge(combined, inflation_factor, on=["location", "sex"])
        .assign(
            deaths=lambda x: x["deaths"] * x["inflation_factor"],
            rates=lambda x: np.where(
                x["deaths"].isnull(), np.nan, x["deaths"] / x["pop"]
            ),
        )
        .drop(columns=["inflation_factor"])
    )

    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        combined.pivot_table(
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

    # For NHPI, use State > National
    # Mix of NHPI county and state level data causes discontinuity in rates
    is_nhpi = pivoted["race"] == "Native Hawaiian or Other Pacific Islander alone"

    pivoted["rates"] = np.where(
        is_nhpi,
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


def process_life_tables() -> pd.DataFrame:
    """Processes male and female life table files (either survivors or life expectancy).

    Data from the UN DESA will be used to calculate mortality rates for ages 85-99 due
    to data from the CDC being unavailable and heavily suppressed for ages 85+. Data
    will be filtered for years 1999-2023 to match CDC years, with age being cut off at
    99 due to lack of data past 100+.

    Raises:
        ValueError: Raise error if incorrect file urls.

    Returns:
        pd.DataFrame: The rates table.
    """

    rates = []

    for file in pathlib.Path("data/undesa").glob("*.xlsx"):
        df = pd.read_excel(
            file,
            sheet_name="Estimates",
            index_col=None,
            header=16,
        )

        filename = file.name
        if "_MALE" in filename:
            sex = "M"
        elif "_FEMALE" in filename:
            sex = "F"
        else:
            raise ValueError("Unknown file type")

        df = (
            df.query(
                "`Region, subregion, country or area *` == 'United States of America'"
            )
            .drop(
                columns=[
                    "Index",
                    "Variant",
                    "Region, subregion, country or area *",
                    "Notes",
                    "Location code",
                    "ISO3 Alpha-code",
                    "ISO2 Alpha-code",
                    "SDMX code**",
                    "Type",
                    "Parent code",
                ]
            )
            .rename(columns={"Year": "year", "Age": "age"})
            .assign(year=lambda x: x["year"].astype(int))
            .query("year >= 1999")
            .melt(
                id_vars="year",
                var_name="age",
                value_name="survivors",
            )
            .assign(sex=sex)
            .sort_values(["year", "age"])
            .reset_index(drop=True)
        )

        df = process_life_rates(df)
        rates.append(df)

    rates = pd.concat(rates, ignore_index=True)

    return rates


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
            age=lambda x: x["age"].replace("100+", "100").astype("int64"),
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
    launch_yr: int,
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
        launch_yr: Launch year.
        pop_df (pd.DataFrame): Population data for the year.
        smooth_s (int): Smoothing factor for spline interpolation. Defaults to 5.
        smooth_k (int): Degree of spline polynomial (1-5). Defaults to 2.

    Returns:
        pd.DataFrame: Death rates broken down by race, sex, and single year
            of age.
    """
    # Death rates calculated from year up to the launch year
    if yr <= launch_yr:
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
        undesa_rates = process_life_tables()

        # UNDESA data only available through 2023. For years beyond 2023, use 2023 data
        # Will need to update once 2024 data becomes available
        undesa_yr = min(cdc_yr, 2023)
        if cdc_yr > 2023:
            logger.warning(
                f"UN DESA data unavailable for {cdc_yr}. Using 2023 data for ages 85-99."
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

    # Death rates are not calculated after the launch year
    else:
        raise ValueError("Death rates not calculated past launch year")
