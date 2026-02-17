import pathlib
import scipy
import numpy as np
import pandas as pd


def get_file_separator(file_path: pathlib.Path) -> str:
    """Determine the appropriate separator based on file extension.

    Args:
        file_path (pathlib.Path): The file path.

    Returns:
        str: The separator character ('\t' for .txt files, ',' for .csv files).
    """
    if file_path.suffix.lower() == ".txt":
        return "\t"
    else:
        return ","


def parse_filename(file_path: pathlib.Path) -> dict:
    """Parses and validates file name matches expected metadata structure.

    Args:
        file_path (pathlib.Path): The file path.

    Raises:
        ValueError: If there are missing/extra/incorrect parts in file name.

    Returns:
        dict: A dictionary of the metadata for each file.
    """

    # Naming for filename structure
    valid_config = {
        0: {
            "name": "location",
            "labels": ["SD", "CA", "US"],
            "map": {"SD": "San Diego County", "CA": "California", "US": "US"},
        },
        1: {
            "name": "product",
            "labels": ["1999-2020", "2018-2023"],
        },
        2: {
            "name": "age_group",
            "labels": ["SYA"],
            "map": {"SYA": "Single-Year Ages"},
        },
        3: {
            "name": "sex",
            "labels": ["F", "M"],
            "map": {"F": "Female", "M": "Male"},
        },
        4: {
            "name": "hispanic",
            "labels": ["NS", "HIS", "NON"],
            "map": {
                "NS": "Not Stated",
                "HIS": "Hispanic or Latino",
                "NON": "Not Hispanic or Latino",
            },
        },
        5: {
            "name": "race",
            "labels": [
                "ASIAN",
                "AIAN",
                "API",
                "BAA",
                "WH",
                "HIS",
                "NHPI",
                "MOR",
                "ALL",
            ],
            "map": {
                "ASIAN": "Asian",
                "AIAN": "American Indian or Alaska Native",
                "API": "Asian",
                "BAA": "Black or African American",
                "WH": "White",
                "HIS": "Hispanic",
                "NHPI": "Native Hawaiian or Other Pacific Islander",
                "MOR": "More than one race",
                "ALL": "ALL",
            },
        },
        6: {
            "name": "year",
            "labels": [str(y) for y in range(1999, 2024)],
        },
        7: {
            "name": "moving_average",
            "labels": ["5Y"],
        },
    }

    parts = file_path.name.split("; ")
    # Strip file extension from last part
    parts[7] = parts[7].split(".")[0]

    if len(parts) != 8:
        raise ValueError(f"Invalid number of parts in file: {file_path}")

    else:
        metadata = {}
        for i, part in enumerate(parts):
            field = valid_config[i]
            key = field["name"]

            if part not in field["labels"]:
                raise ValueError(f"Invalid value for {key}: {part}")
            else:
                metadata[key] = field["map"][part] if "map" in field else (part)

    return metadata


def validate_file_name(file_path: pathlib.Path) -> None:
    """Validates that metadata matches the query metadata in the file's Notes column.

    Args:
        file_path (pathlib.Path): The file path.

    Raises:
        ValueError: If any mismatch is found between the file content and the metadata.
    """

    metadata = parse_filename(file_path)

    # Create a check for moving average
    year_check = "; ".join(str(int(metadata["year"]) - i) for i in reversed(range(5)))

    separator = get_file_separator(file_path)
    df = pd.read_csv(file_path, sep=separator)

    if "Notes" not in df.columns:
        raise ValueError("Missing Notes column for validation")

    notes = df["Notes"].astype(str)

    # Age Group Validation
    if ("Single-Year Ages" in df.columns) and (
        metadata["age_group"] != "Single-Year Ages"
    ):
        raise ValueError("Incorrect age specification")

    # Sex and Hispanic Validation
    single_value_checks = {
        "sex": "Sex",
        "hispanic": "Hispanic Origin",
    }

    for key, label in single_value_checks.items():
        if not notes.str.contains(f"{label}: {metadata[key]}").any():
            raise ValueError(f"Incorrect {key} value")

    # Location Validation
    if metadata["location"] == "US" and notes.str.contains("States").any():
        raise ValueError("Incorrect national location")
    elif metadata["location"] != "US":
        if not notes.str.contains(f"States: {metadata['location']}").any():
            raise ValueError("Incorrect city or state location")

    # Year Validation
    if not notes.str.contains(f"Year/Month: {year_check}").any():
        raise ValueError("Incorrect year(s)")

    # Check for 1999-2020 formatting
    if metadata["product"] == "1999-2020":
        if (~notes.str.contains(f"Race: {metadata['race']}").any()) and metadata[
            "race"
        ] not in ["Hispanic", "ALL"]:
            raise ValueError("Incorrect race metadata (1999-2020)")
        elif (notes.str.contains(f"Race: {metadata['race']}").any()) and metadata[
            "race"
        ] in ["Hispanic", "ALL"]:
            raise ValueError("Incorrect race metadata (1999-2020)")

    # Check for 2018-2023 formatting
    elif metadata["product"] == "2018-2023":
        if (
            ~notes.str.contains(f"Single Race 6: {metadata['race']}").any()
        ) and metadata["race"] not in [
            "Hispanic",
            "ALL",
        ]:
            raise ValueError("Incorrect race metadata (2018-2023)")

        if (
            notes.str.contains(f"Single Race 6: {metadata['race']}").any()
        ) and metadata["race"] in [
            "Hispanic",
            "ALL",
        ]:
            raise ValueError("Incorrect race metadata (2018-2023)")


def transform_CDC_1999(file_path: pathlib.Path) -> pd.DataFrame:
    """Parse the text files and transform the file into a DataFrame.

    Filter for only the 1999-2020 CDC product and ages 84 and under. Populate location
    and year for each row. Assign "Hispanic" race to all rows missing a race.

    Args:
        file_path (pathlib.Path): The file path.

    Returns:
        pd.DataFrame: A processed dataframe for the first CDC product.
    """

    # Get metadata dict for column assignment
    metadata = parse_filename(file_path)

    # Ages to be excluded from dataset
    excluding_sya = [str(age) for age in range(85, 101)]

    required_columns = [
        "Single-Year Ages Code",
        "Sex Code",
        "Hispanic Origin",
        "Race",
        "Year",
        "Deaths",
        "Population",
    ]

    column_map = {
        "Single-Year Ages Code": "age",
        "Sex Code": "sex",
        "Hispanic Origin": "hispanic origin",
        "Race": "race",
        "Year": "year",
        "Deaths": "deaths",
        "Population": "pop",
        "Location": "location",
    }

    separator = get_file_separator(file_path)
    df = (
        pd.read_csv(file_path, sep=separator)
        .pipe(lambda x: (x.loc[: x[x["Notes"] == "---"].index.min() - 1]))
        .loc[:, lambda x: [col for col in required_columns if col in x.columns]]
        .rename(columns=column_map, errors="ignore")
        .assign(
            race=lambda x: x["race"] if "race" in x.columns else "Hispanic",
            location=metadata["location"],
            year=metadata["year"],
            product=metadata["product"],
        )
        .query("age not in @excluding_sya and product == '1999-2020'")
        .replace(
            {
                "Asian or Pacific Islander": "Asian alone",
                "Black or African American": "Black or African American alone",
                "American Indian or Alaska Native": "American Indian or Alaska Native alone",
                "White": "White alone",
                "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Islander alone",
            }
        )
    )

    # If race is ALL, duplicate data for both NHPI and MOR
    if metadata["race"] == "ALL":
        df_nhpi = df.copy()
        df_nhpi["race"] = "Native Hawaiian or Other Pacific Islander alone"
        df_mor = df.copy()
        df_mor["race"] = "Two or More Races"
        df = pd.concat([df_nhpi, df_mor], ignore_index=True)

    return df


def transform_CDC_2018(file_path: pathlib.Path) -> pd.DataFrame:
    """Parse the text files and transform the file into a DataFrame.

    Filter for only the 2018-2023 CDC product and ages 84 and under. Populate location
    and year for each row. Collapse multiple race columns into one titled "race".
    Assign "race" for races with no race column.

    Args:
        file_path (pathlib.Path): The file path.

    Returns:
        pd.DataFrame: A processed dataframe for the second CDC product.
    """

    # Get metadata dict for column assignment
    metadata = parse_filename(file_path)

    # Ages to be excluded from dataset
    excluding_sya = [str(age) for age in range(85, 101)]

    required_columns = [
        "Single-Year Ages Code",
        "Sex Code",
        "Hispanic Origin",
        "Single Race 6",
        "Year",
        "Deaths",
        "Population",
    ]

    column_map = {
        "Single-Year Ages Code": "age",
        "Sex Code": "sex",
        "Hispanic Origin": "hispanic origin",
        "Year": "year",
        "Single Race 6": "race",
        "Deaths": "deaths",
        "Population": "pop",
        "Location": "location",
    }

    separator = get_file_separator(file_path)
    df = (
        pd.read_csv(file_path, sep=separator)
        .pipe(lambda x: (x.loc[: x[x["Notes"] == "---"].index.min() - 1]))
        .loc[:, lambda x: [col for col in required_columns if col in x.columns]]
        .rename(columns=column_map, errors="ignore")
        .assign(
            race=lambda x: x["race"] if "race" in x.columns else "Hispanic",
            location=metadata["location"],
            year=metadata["year"],
            product=metadata["product"],
        )
        .query("age not in @excluding_sya and product == '2018-2023'")
    )

    # Ensure proper copy before race transformation to avoid view issues
    df = df.copy()

    # Replace race values explicitly on the race column
    df["race"] = df["race"].replace(
        {
            "Asian or Pacific Islander": "Asian alone",
            "Asian": "Asian alone",
            "Black or African American": "Black or African American alone",
            "American Indian or Alaska Native": "American Indian or Alaska Native alone",
            "White": "White alone",
            "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Islander alone",
            "More than one race": "Two or More Races",
        }
    )

    return df


def parse_not_stated(df: pd.DataFrame) -> pd.DataFrame:
    """Parse through CDC WONDER to calculate inflation factor for "not stated" data.

    The CDC WONDER contains multiple rows marked as "Not Stated"/"NS". This function
    combs through the datasets and locates the number of not stated deaths versus stated
    deaths and separates them by geography, sex, and year. It then calculates an
    inflation factor for each combination.

    Args:
        df (pd.DataFrame): A DataFrame containing mortality data.

    Returns:
        pd.DataFrame: A processed DataFrame with year, geography, sex, and inflation
            factor.
    """

    ns, stated = [], []

    # Comb through data files
    for file_path in pathlib.Path("data/deaths/cdc_wonder/stated_not_stated").rglob(
        "*"
    ):
        if file_path.is_file():

            parts = file_path.name.split("; ")

            # Read in data
            df = (
                pd.read_csv(file_path)
                .rename(columns=str.lower)
                .loc[:, ["sex", "deaths"]]
                .dropna()
                .assign(
                    location=parts[0],
                    sex=lambda x: x["sex"].replace({"Male": "M", "Female": "F"}),
                    deaths=lambda x: pd.to_numeric(
                        x["deaths"].replace({"Suppressed": "0"}), errors="coerce"
                    ),
                    year=int(parts[6]),
                )
                .assign(
                    location=lambda x: x["location"].replace(
                        {"SD": "San Diego County", "CA": "California"}
                    )
                )
            )

            # Separate data by status
            if "NS" in file_path.name.upper():
                df["status"] = "not stated"
                ns.append(df)
            else:
                df["status"] = "stated"
                stated.append(df)

    # Concatenate all DataFrames into one
    ns = (
        pd.concat(ns, ignore_index=True)
        .groupby(["year", "location", "sex"], as_index=False)["deaths"]
        .sum()
        .assign(status="not stated")
    )
    stated = pd.concat(stated, ignore_index=True)

    # Merge and create inflation factor
    merged = (
        pd.merge(
            ns,
            stated,
            on=["year", "location", "sex"],
            suffixes=("_not_stated", "_stated"),
        ).assign(
            inflation_factor=lambda x: 1 + (x["deaths_not_stated"] / x["deaths_stated"])
        )
    ).drop(
        columns=[
            "deaths_not_stated",
            "status_not_stated",
            "deaths_stated",
            "status_stated",
        ]
    )

    return merged


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

    data = parse_not_stated(df)

    # Create a filtered DataFrame for "Stated" responses
    stated_df = df.assign(
        deaths=pd.to_numeric(df["deaths"], errors="coerce"),
        pop=pd.to_numeric(df["pop"], errors="coerce"),
        year=pd.to_numeric(df["year"], errors="coerce"),
    ).query("(`hispanic origin` != 'Not Stated' and age != 'NS')")

    results = (
        pd.merge(stated_df, data, on=["year", "location", "sex"])
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
        - Impute using deaths_recode

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
        return row["rate_imputed"], "Imputation"


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
            national[["year", "age", "race", "sex", "hispanic origin", "rates"]],
            on=["year", "age", "race", "sex", "hispanic origin"],
            how="left",
            suffixes=("", "_national"),
        )
        .rename(columns={"rates": "rates_county"})
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
                lambda row: deaths_recode(row["deaths"], row["pop"]) / row["pop"],
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
                "deaths",
                "location",
                "rate_prev",
                "rate_next",
                "rate_avg",
                "rate_imputed",
            ]
        )
    )

    return county_merged


def load_local_files(pop_df: pd.DataFrame) -> pd.DataFrame:
    """Load files from a directory, process them, and combined them into one by product.

    Args:
        pop_df (pd.DataFrame): Population dataframe from CCM for 2018-2023
            product population estimates.

    Returns:
        pd.DataFrame: A single DataFrame composed of 2003-2023 data for
        ages 0-99 from the CDC.
    """

    data_by_product = {
        "1999-2020": {"San Diego County": [], "California": [], "US": []},
        "2018-2023": {"San Diego County": [], "California": [], "US": []},
    }

    transform_map = {
        "1999-2020": transform_CDC_1999,
        "2018-2023": transform_CDC_2018,
    }

    for file_path in pathlib.Path("data/deaths/cdc_wonder/geographic").rglob("*"):
        if file_path.is_file():
            meta = parse_filename(file_path)
            validate_file_name(file_path)

            product = meta["product"]
            transform_fn = transform_map.get(product)
            if not transform_fn:
                print(f"Unsupported product: {product}")
                continue

            df = transform_fn(file_path)
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
        .query("age <= 99")
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
    as a substitute for year 2021. Smoothing is applied to the combined rates using
    spline interpolation to reduce discontinuities across ages.

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
    # Death rates calculated from base year up to the launch year
    if yr <= launch_yr:
        # For the Social Security Actuarial Life Table dataset
        # If current year is not available grab the most recent available year
        if yr not in ss_life_tbl["year"].unique():
            ss_yr = ss_life_tbl["year"][ss_life_tbl["year"] <= yr].max()
            print(
                f"Warning: Social Security Actuarial Life Table dataset unavailable for {yr}. "
                f"Defaulting to most recent dataset: {ss_yr}"
            )
        else:
            ss_yr = yr

        # Social Security Actuarial Life Table dataset
        # Years 2020 and 2021 not used due to COVID-19 impact on geriatric death rates
        # Default to 2019 data
        if ss_yr in [2020, 2021]:
            ss_yr = 2019
            print(
                "Warning: Social Security Actuarial Life Table dataset not used for 2020/2021. "
                "Defaulting to 2019 data."
            )

        # Load and process CDC WONDER mortality data
        mortality_df = load_local_files(pop_df=pop_df)

        # Year 2021 not available, use 2020 data instead
        if yr == 2021:
            cdc_yr = 2020
            print("Warning: CDC WONDER data unavailable for 2021. " "Using 2020 data.")
        else:
            cdc_yr = yr

        # Filter to the CDC year and ages < 85, keep only necessary columns
        cdc_rates = mortality_df.query("year == @cdc_yr and age < 85")[
            ["race", "sex", "age", "rates"]
        ].rename(columns={"rates": "rate_death"})

        # Get unique race categories from CDC data
        race_categories = cdc_rates["race"].unique()

        # Filter Social Security Actuarial Life Table to chosen year and ages >= 85
        ss_rates = ss_life_tbl.query("year == @ss_yr and age >= 85")[
            ["age", "sex", "rate"]
        ].rename(columns={"rate": "rate_death"})

        # Expand SS rates to include all race categories
        # (SS life table doesn't have race breakdown, so apply same rates to all races)
        ss_expanded = []
        for race in race_categories:
            ss_race = ss_rates.copy()
            ss_race["race"] = race
            ss_expanded.append(ss_race)

        ss_rates_expanded = pd.concat(ss_expanded, ignore_index=True)

        # Combine CDC rates (ages 0-84) with Social Security rates (ages 85+)
        rates = pd.concat([cdc_rates, ss_rates_expanded], ignore_index=True)

        # Apply smoothing if requested
        if smooth_s is not None and smooth_k is not None:
            # Prepare DataFrame for smooth_rates function
            rates_for_smoothing = rates.copy()
            rates_for_smoothing["year"] = cdc_yr
            rates_for_smoothing = rates_for_smoothing.rename(
                columns={"race": "race/ethnicity", "rate_death": "rates"}
            )

            # Apply smoothing
            smoothed = smooth_rates(rates_for_smoothing, s=smooth_s, k=smooth_k)

            # Rename columns back and update rates
            rates["rate_death"] = smoothed["rates"].values

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
