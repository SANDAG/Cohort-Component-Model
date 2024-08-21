"""Get group quarters and household formation rates by race, sex, and single year of age."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import pandas as pd
from python.utilities import adjust_sum, distribute_excess
import sqlalchemy as sql
import warnings


def get_formation_rates(
    yr: int,
    launch_yr: int,
    pums_persons: str,
    sandag_estimates: dict,
    engine: sql.engine,
) -> pd.DataFrame:
    """Generate group quarters and household formation rates broken
    down by race, sex, and single year of age.

    Group quarter and household formation rates are calculated using the
    5-year ACS PUMS persons. Prior to calculation, the total number of
    households, group quarters, and population are scaled to match SANDAG
    Estimates for the increment year from the vintage associated with the
    launch year.

    Note that formation rates for persons over 70 are calculated as a
    single composite rate for all persons over 70, where group quarters rates
    are calculated within sex and household formation rates within race and
    sex. These rates are then applied uniformly to all single year of age
    categories above 70.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pums_persons (str): 5-year ACS PUMS persons query file
        sandag_estimates (dict): loaded JSON control totals from historical
            SANDAG Estimates programs
        engine (sql.engine): SQLAlchemy MSSQL connection engine

    Returns:
        pd.DataFrame: Group quarters and household formation rates broken down
            by race, sex, and single year of age
    """
    if yr <= launch_yr:
        # Load SQL queries and apply checks to datasets
        with engine.connect() as connection:
            # Load ACS PUMS persons
            with open(pums_persons, "r") as query:
                pums_persons_df = pd.read_sql_query(
                    query.read().format(yr=yr), connection
                )
        if len(pums_persons_df.index) == 0:
            raise ValueError(str(yr) + ": not in ACS 5-year PUMS")

        # Take total households/group quarters/population and apply scaling factor
        # Matching the SANDAG Estimates Program for the increment year
        # From the vintage associated with the chosen launch year
        control_map = {
            "households": {"col": "pop_hh_head", "control": "hh"},
            "population": {"col": "pop", "control": "pop"},
            "population": {"col": "pop_gq", "control": "gq"},
        }

        for k, v in control_map.items():
            control = sandag_estimates[str(launch_yr)][str(yr)][k][v["control"]]
            if control is not None:
                scale_pct = control / pums_persons_df[v["col"]].sum()
                pums_persons_df[v["col"]] = pums_persons_df[v["col"]] * scale_pct
            else:
                warnings.warn(
                    "No " + v["control"] + " control total provided.", UserWarning
                )

        # Distribute excess head of household and group quarters population
        # This is done to avoid formation rates > 1
        pums_persons_df["pop_gq"] = distribute_excess(
            df=pums_persons_df, subset="pop_gq", total="pop"
        )
        pums_persons_df["pop_hh_head"] = distribute_excess(
            df=pums_persons_df, subset="pop_hh_head", total="pop_hh"
        )

        # Calculate the over 70 Group Quarters Formation Rate by Sex
        rates_70plus_gq = (
            pums_persons_df[pums_persons_df["age"] > 70]
            .groupby(["sex"])[["pop_gq", "pop"]]
            .sum()
            .reset_index()
            .assign(rate_gq=lambda x: x["pop_gq"] / x["pop"])[["sex", "rate_gq"]]
        )

        # Calculate the over 70 Household Formation Rate by Race and Sex
        rates_70plus_hh_head = (
            pums_persons_df[pums_persons_df["age"] > 70]
            .groupby(["race", "sex"])[["pop_hh_head", "pop_hh"]]
            .sum()
            .reset_index()
            .assign(rate_hh=lambda x: x["pop_hh_head"] / x["pop_hh"])[
                ["race", "sex", "rate_hh"]
            ]
        )

        # For age categories over 70, assign all over 70 Formation rates
        # To all race, sex, and single year of age categories
        rates_70plus = (
            pums_persons_df[pums_persons_df["age"] > 70]
            .merge(right=rates_70plus_gq, how="left", on="sex")
            .merge(right=rates_70plus_hh_head, how="left", on=["race", "sex"])
            .fillna(0)[["race", "sex", "age", "rate_gq", "rate_hh"]]
        )

        # Calculate the <=70 Group Quarters and Household Formation Rates
        rates_70under = (
            pums_persons_df[pums_persons_df["age"] <= 70]
            .assign(rate_gq=lambda x: x["pop_gq"] / x["pop"])
            .assign(rate_hh=lambda x: x["pop_hh_head"] / x["pop_hh"])
            .fillna(0)[["race", "sex", "age", "rate_gq", "rate_hh"]]
        )

        # Combine Formation Rates
        # Adjust categories where sum of formation rates > 1
        rates = pd.concat([rates_70under, rates_70plus], ignore_index=True)
        rates[["rate_gq", "rate_hh"]] = adjust_sum(
            df=rates, cols=["rate_gq", "rate_hh"], sum=1, option="exceeds"
        )

        return rates

    # Formation rates are not calculated after the launch year
    else:
        raise ValueError("Formation rates not calculated past launch year")
