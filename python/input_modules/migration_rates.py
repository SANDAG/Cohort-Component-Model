"""Get migration rates by race, sex, and single year of age."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import pandas as pd
import numpy as np
import sqlalchemy as sql
import yaml

from python.utils import ROOT_FOLDER

def get_migration_rates(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    engine: sql.Engine,
) -> pd.DataFrame:
    """Create migration rates broken down by race, sex, and single year of age.

    Merge the population dataset with the 5-year ACS PUMS count of in/out
    migrants for San Diego County. Calculate the crude migration rate within
    race, sex, and single year of age capping the rates at 20% within each
    category removing active-duty military population from the calculation.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age
        pums_migrants (str): query to get 5-year ACS PUMS in/out
            migrants for San Diego County
        engine (sql.Engine): SQLAlchemy MSSQL connection engine

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """
    # Migration rates calculated from base year up to the launch year
    if yr <= launch_yr:
        return calculate_migration_rates(
            yr=yr,
            pop_df=pop_df,
            pums_migrants=pums_migrants,
            engine=engine,
            cap_rates=True,
        )

    # Migration rates are not calculated after the launch year
    # Post-launch rates are controlled to annual migration totals when provided.
    else:
        return control_migration_rates(
            yr=yr,
            launch_yr=launch_yr,
            pop_df=pop_df,
            pums_migrants=pums_migrants,
            engine=engine,
        )

def calculate_migration_rates(
    yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    engine: sql.Engine,
    cap_rates: bool = True,
) -> pd.DataFrame:
    """Calculate migration rates for a specific source year.

    Args:
        yr: Source year for ACS PUMS migrants query
        pop_df (pd.DataFrame): Population data by race, sex, and age
        pums_migrants (str): SQL query path for ACS PUMS in/out migrants
        engine (sql.Engine): SQLAlchemy MSSQL connection engine
        cap_rates: Whether to cap rates at 20%

    Returns:
        pd.DataFrame: Migration rates by race, sex, and age
    """
    with engine.connect() as connection:
        with open(pums_migrants, "r") as query:
            pums_migrants_df = pd.read_sql_query(query.read().format(yr=yr), connection)

        if len(pums_migrants_df.index) == 0:
            raise ValueError(str(yr) + ": not in ACS PUMS in/out migrants")

    df = (
        pop_df.merge(
            right=pums_migrants_df,
            how="left",
            on=["race", "sex", "age"],
        )
        .assign(pop_civ=lambda x: x["pop"] - x["pop_mil"])
        .assign(
            rate_in=lambda x: np.where(
                x["pop_civ"] > 0,
                x["in"] / x["pop_civ"],
                0,
            )
        )
        .assign(
            rate_out=lambda x: np.where(
                x["pop_civ"] > 0,
                x["out"] / x["pop_civ"],
                0,
            )
        )
        .fillna(0)
    )

    # Guard against division edge cases that can produce +/-inf.
    df[["rate_in", "rate_out"]] = df[["rate_in", "rate_out"]].replace(
        [np.inf, -np.inf], 0
    )

    if cap_rates:
        # Cap crude migration rates at 20%
        df["rate_in"] = np.where(df["rate_in"] > 0.2, 0.2, df["rate_in"])
        df["rate_out"] = np.where(df["rate_out"] > 0.2, 0.2, df["rate_out"])

    return df[["race", "sex", "age", "rate_in", "rate_out"]]

def control_migration_rates(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    engine: sql.Engine,
) -> pd.DataFrame:
    """Get post-launch migration rates controlled to annual totals.

    Uses launch-year crude rates as baseline then scales to post-launch
    migration control totals for the current year.
    """
    with open(ROOT_FOLDER / "config.yml") as f:
        config = yaml.safe_load(f)

    migration_controls_fp = config["csv"].get("migration_controls")
    if migration_controls_fp is None:
        raise ValueError("Migration rates not calculated past launch year")

    migration_controls_df = pd.read_csv(migration_controls_fp)
    migration_controls = get_migration_controls(migration_controls_df)

    # Build launch-year baseline rates without capping; cap after control scaling.
    base_rates = calculate_migration_rates(
        yr=launch_yr,
        pop_df=pop_df,
        pums_migrants=pums_migrants,
        engine=engine,
        cap_rates=False,
    )

    df = (
        pop_df[["race", "sex", "age", "pop", "pop_mil"]]
        .merge(base_rates, how="left", on=["race", "sex", "age"])
        .fillna(0)
        .assign(pop_civ_surv=lambda x: x["pop"] - x["pop_mil"])
    )

    df = scale_migration_rates_to_controls(
        df=df,
        yr=yr,
        migration_controls=migration_controls,
    )

    # Cap controlled migration rates at 20%
    df["rate_in"] = np.where(df["rate_in"] > 0.2, 0.2, df["rate_in"])
    df["rate_out"] = np.where(df["rate_out"] > 0.2, 0.2, df["rate_out"])

    return df[["race", "sex", "age", "rate_in", "rate_out"]]

def get_migration_controls(df: pd.DataFrame) -> dict:
    """Convert migration controls CSV data into yearly control dictionary.

    Expected columns are: year, ins, outs
    """
    with open(ROOT_FOLDER / "config.yml") as f:
        config = yaml.safe_load(f)

    start_yr = config["interval"]["launch"] + 1
    end_yr = config["interval"]["horizon"]

    if start_yr > end_yr:
        raise ValueError("Invalid migration controls interval: start_yr > end_yr")

    required_cols = {"year", "ins", "outs"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Migration controls CSV must contain columns: year, ins, outs")

    if df["year"].dropna().duplicated().any():
        raise ValueError("Migration controls CSV contains duplicate year values")

    required_years = {str(yr) for yr in range(start_yr, end_yr + 1)}
    provided_years = {str(int(yr)) for yr in df["year"].dropna()}
    missing_years = sorted(required_years - provided_years, key=int)

    if missing_years:
        missing_years_str = ", ".join(missing_years)
        raise ValueError(
            "Migration controls CSV is missing years required by config interval "
            f"[{start_yr}, {end_yr}]: {missing_years_str}"
        )

    controls = {}
    for _, row in df.iterrows():
        if pd.isna(row["year"]):
            raise ValueError("Migration controls CSV contains missing year values")

        year = str(int(row["year"]))
        in_control = row["ins"]
        out_control = row["outs"]

        controls[year] = {
            "in": None if pd.isna(in_control) else int(in_control),
            "out": None if pd.isna(out_control) else int(out_control),
        }

    return controls

def scale_migration_rates_to_controls(
    df: pd.DataFrame,
    yr: int,
    migration_controls: dict | None,
) -> pd.DataFrame:
    """Scale migration rates to match optional yearly in/out control totals.

    This applies scale factors to rate_in/rate_out using the same exposure
    base used in the annual cycle (survived civilian population).
    """
    if migration_controls is None:
        return df

    year_controls = migration_controls.get(str(yr))
    if not year_controls:
        return df

    control_in = year_controls.get("in")
    control_out = year_controls.get("out")

    exposure = df["pop_civ_surv"].astype(float)

    if control_in is not None:
        control_in = int(control_in)
        if control_in < 0:
            raise ValueError("Migration control totals must be non-negative")

        expected_in = float((exposure * df["rate_in"].astype(float)).sum())
        if control_in > 0 and expected_in == 0:
            raise ValueError(
                f"{yr}: in-migration control ({control_in}) cannot be matched because expected in-migration is 0"
            )

        if expected_in > 0:
            df["rate_in"] = df["rate_in"].astype(float) * (control_in / expected_in)

    if control_out is not None:
        control_out = int(control_out)
        if control_out < 0:
            raise ValueError("Migration control totals must be non-negative")

        out_capacity = int(exposure.sum())
        if control_out > out_capacity:
            raise ValueError(
                f"{yr}: out-migration control ({control_out}) exceeds survived civilian population ({out_capacity})"
            )

        expected_out = float((exposure * df["rate_out"].astype(float)).sum())
        if control_out > 0 and expected_out == 0:
            raise ValueError(
                f"{yr}: out-migration control ({control_out}) cannot be matched because expected out-migration is 0"
            )

        if expected_out > 0:
            df["rate_out"] = df["rate_out"].astype(float) * (
                control_out / expected_out
            )

    return df
