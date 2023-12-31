"""This module contains all utilities associated with exporting data."""
import os.path
import pandas as pd


def write_df(yr: int, df: pd.DataFrame, fn: str) -> None:
    """Write DataFrame for increment year."""
    df = df.sort_values(by=["race", "sex", "age"])
    df.insert(0, "year", yr)

    if os.path.isfile(fn):
        df.to_csv(fn, mode="a", index=False, header=False)
    else:
        df.to_csv(fn, mode="w", index=False)


def write_rates(yr: int, rates: dict, fn: str) -> None:
    """Write calculated rates for increment year."""
    output = None
    for rate in rates:
        if output is None:
            output = rates[rate]
        else:
            output = output.merge(
                right=rates[rate], how="outer", on=["race", "sex", "age"]
            )

    write_df(yr=yr, df=output, fn=fn)
