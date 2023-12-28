"""This module contains generic utilities."""

import numpy as np
import pandas as pd
from typing import List


def adjust_sum(
    df: pd.DataFrame, cols: List[str], sum: float, option: str
) -> pd.DataFrame:
    """Adjust row values for columns such that sum equals or does not exceed
    specified value. Use for positive vales only.

    Args:
        df (pd.DataFrame): Input DataFrame
        cols (List[str]): List of column names
        sum (float): Asserted value
        option (str): Set to 'equals' or 'exceeds'

    Returns:
        pd.DataFrame: Returns adjusted input DataFrame columns
    """
    # Check columns are integer or floating point data types
    if sum > 0:
        if all(x.kind in "if" for x in df[cols].dtypes.tolist()):
            if option == "equals":
                return df[cols].apply(
                    lambda x: x * (sum / x.sum()) if x.sum() > 0 else x, axis=1
                )
            elif option == "exceeds":
                return df[cols].apply(
                    lambda x: x * (sum / x.sum()) if x.sum() > sum else x, axis=1
                )
            else:
                return ValueError(
                    "Parameter 'option': must be one of 'equals' or 'exceeds'."
                )
        else:
            return ValueError("All columns must be integer or floating point.")
    else:
        return ValueError("Parameter: 'sum': must be > 0")


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
