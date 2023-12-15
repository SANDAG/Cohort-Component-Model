"""This module contains generic utilities."""

import numpy as np
import pandas as pd


def distribute_excess(df: pd.DataFrame, subset: str, total: str):
    """Distribute excess numeric values.

    Distribute excess value from records where numeric value contained in a
    column exceeds the total numerical value defined in another column from
    the same input DataFrame.

    Excess value is distributed to records using the distribution of existing
    numeric values in the column.

    Args:
        df (pd.DataFrame): Input DataFrame
        subset (str): Column name containing subset of numeric value of
            column identified as the total numerical value
        total (str): Column name containing total numerical value

    Returns:
        pd.Series: Records with excess value re-distributed
    """
    df = df[[subset, total]].copy()

    # Check columns are integer or floating point data types
    if df[subset].dtype.kind in "if" and df[total].dtype.kind in "if":
        # Distribute excess numeric value from records where numeric values
        # In the subset column exceed numeric values in the total column
        # To records where the numeric value of the subset column
        # Do not equal or exceed numeric values in the total column
        # Using the distribution of subset column numeric values
        excess = (
            df[df[subset] > df[total]][subset].sum()
            - df[df[subset] > df[total]][total].sum()
        )

        while excess > 0:
            df[subset] = np.where(df[subset] > df[total], df[total], df[subset])

            condition = df[subset] < df[total]

            df.loc[condition, subset] = df.loc[condition][subset] + (
                excess * df.loc[condition][subset] / df.loc[condition][subset].sum()
            )

            excess = (
                df[df[subset] > df[total]][subset].sum()
                - df[df[subset] > df[total]][total].sum()
            )

        return df[subset]

    else:
        return ValueError("All columns must be integer or floating point.")
