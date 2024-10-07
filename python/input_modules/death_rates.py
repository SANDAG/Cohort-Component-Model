"""Get crude death rates by race, sex, and single year of age."""

# TODO: (6-feature) Add function to allow for input % adjustments to death rates.
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def deaths_recode(deaths: str, pop: str) -> float:
    """Recode WONDER deaths 0 and "Suppressed" values."""
    pop = int(pop)  # floor function on floats
    if deaths == "0":
        if pop > 0:
            return 1
        else:
            return 0
    elif deaths == "Suppressed":
        if pop > 4:
            return 4.5
        elif pop > 0:
            return 1
        else:
            return 0
    else:
        return float(deaths)


def get_death_rates(
    yr: int, launch_yr: int, ss_life_tbl: pd.DataFrame, rates_map: dict
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

    Note: Death rates are a prime candidate for a smoothing function to avoid
    discontinuities, range bounded > 0 and < 1.

    Args:
        yr: Increment year
        launch_yr: Launch year
        ss_life_tbl (pd.DataFrame): Social Security Actuarial Life Table from
            death_rates.load_ss_life_tbl
        rates_map (dict): loaded JSON configuration birth/death rate map

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
                + ". Default to most recent dataset: "
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
                "Social Security Actuarial Life Table dataset not used for 2020/2021. Default to 2019 data."
            )

        if str(yr) not in rates_map["deaths"].keys():
            raise ValueError("No death rate mapping for: " + str(yr))

        # Filter the Social Security Actuarial Life Table to the chosen year
        # Remove records where age < 85
        ss_life_tbl = ss_life_tbl[
            (ss_life_tbl["year"] == ss_yr) & (ss_life_tbl["age"] >= 85)
        ]

        rates = pd.DataFrame()
        # For each WONDER death rate file path in the chosen base year
        for k, v in rates_map["deaths"][str(yr)].items():
            fp = "data/deaths/" + str(yr) + "/" + v

            # Get WONDER death rate data for ages < 85
            wonder_rates = (
                pd.read_csv(
                    fp,
                    delimiter="\t",
                    usecols=[
                        "Gender Code",
                        "Single-Year Ages Code",
                        "Deaths",
                        "Population",
                    ],
                    dtype={
                        "Gender Code": str,
                        "Single-Year Ages Code": str,
                        "Deaths": str,
                        "Population": str,
                    },
                )
                .rename(
                    columns={
                        "Gender Code": "sex",
                        "Single-Year Ages Code": "age",
                        "Deaths": "deaths",
                        "Population": "pop",
                    }
                )
                .dropna(subset=["sex", "age"])
                .assign(race=k)
                .astype({"age": "int", "pop": "int"})
                .query("age < 85")
            )

            # Recode 0 deaths to 1, Recode Suppressed deaths to 4.5
            wonder_rates["deaths"] = wonder_rates.apply(
                lambda x: deaths_recode(x["deaths"], x["pop"]), axis=1
            )

            # Calculate crude death rate
            wonder_rates["rate"] = wonder_rates["deaths"] / wonder_rates["pop"]
            wonder_rates = wonder_rates[["race", "sex", "age", "rate"]]

            # Add Social Security Actuarial Life Table rates for each race
            ss_rates = ss_life_tbl.assign(race=k)[["race", "sex", "age", "rate"]]

            rates = pd.concat([rates, wonder_rates, ss_rates])

        return rates.rename(columns={"rate": "rate_death"})

    # Death rates are not calculated after the launch year
    # TODO: (6-feature) Adjustments to death rates would be made post-launch year through horizon
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
