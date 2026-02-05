"""This module contains generic utilities."""

import pathlib

import math
import numpy as np
import pandas as pd
import sqlalchemy as sql
import yaml


#########
# PATHS #
#########

# Store project root folder
ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent


#####################
# SQL CONFIGURATION #
#####################

# Load secrets YAML file
try:
    with open(ROOT_FOLDER / "secrets.yml", "r") as file:
        _secrets = yaml.safe_load(file)
except IOError:
    raise IOError("secrets.yml does not exist, see README.md")

# Create SQLAlchemy engine(s)
SQL_ENGINE = sql.create_engine(
    "mssql+pymssql://" + _secrets["sql"]["server"] + "/" + _secrets["sql"]["database"]
)


##############################
# UTILITY LISTS AND MAPPINGS #
##############################

RANDOM_SEED = 42  # Seed for random number generation to ensure reproducibility


#####################
# UTILITY FUNCTIONS #
#####################


def _adjust_weights(x: list[float | int], w: list[float | int]) -> list[list]:
    """Adjust weighted moving average weights.

    This function adjusts a single set of weighted moving average weights
    to account for time series boundaries that interfere with the moving
    average window. Weights that are unable to be used are added to the
    closest weight that is able to be used. This results in a set of weights
    that are specific to each time series record.

    Note, the window is assumed to be symmetric. Users can input weights of
    0 within the window to create asymmetric windows.
        w = [0, 1, 0] - No average is taken of the original record
        w = [0.25, 0.5, 0.25] - Take 25% of previous, 50% original, 25% subsequent
        w = [0.25, 0.75, 0] - Take 25% of previous, 75% original

    Args:
        x (list[float|int]): The time series records to take a moving average of
        w (list[float|int]): The weighted moving average window and weights

    Returns:
        list[list[float|int]]: Weighted moving average windows and weights for
            each time series record that will have a weighted moving average taken
    """
    # Weights are assumed to be symmetric
    # Users can input 0 values for asymmetric weights
    if len(w) % 2 != 1:
        raise ValueError("Weights must be symmetric.")

    # For each record that will have a weighted moving average applied to it
    weights = []
    for i in range(len(x)):
        weight = []
        adjustment = 0

        # Look backwards and adjust weights such that backward-looking weights
        # That cannot be used are added to the next weight that is able to be used
        for j in range(len(w)):
            if i + j - len(w) // 2 < 0:
                weight.append(0)
                adjustment += w[j]
            else:
                weight.append(w[j] + adjustment)
                adjustment = 0

        # Look forwards and adjust weights such that forward-looking weights
        # That cannot be used are added to the prior weight that is able to be used
        for j in range(len(w) - 1, -1, -1):
            if i + j - len(w) // 2 >= len(x):
                weight[j] = 0
                adjustment += w[j]
            else:
                weight[j] = w[j] + adjustment
                break  # stop once weight can be used

        # Weights are now record-specific
        weights.append(weight)

    return weights


def adjust_sum(
    df: pd.DataFrame, cols: list[str], sum: float, option: str
) -> pd.DataFrame:
    """Adjust row values for columns such that sum equals or does not exceed
    specified value. Use for positive values only.

    Args:
        df (pd.DataFrame): Input DataFrame
        cols (list[str]): List of column names
        sum (float): Asserted value
        option (str): Set to 'equals' or 'exceeds'

    Returns:
        pd.DataFrame: Returns adjusted input DataFrame columns
    """
    # Check columns are integer or floating point data types
    if sum > 0:
        if all(x.kind in "if" for x in df[cols].dtypes.tolist()):
            # Convert columns to float64 data type for added precision
            # This minimizes floating point errors in scaling
            df[cols] = df[cols].astype(np.float64)

            if option == "equals":
                return df[cols].apply(
                    lambda x: x * (sum / x.sum()) if x.sum() > 0 else x, axis=1
                )  # type: ignore
            elif option == "exceeds":
                return df[cols].apply(
                    lambda x: x * (sum / x.sum()) if x.sum() > sum else x,
                    axis=1,
                )  # type: ignore
            else:
                raise ValueError(
                    "Parameter 'option': must be one of 'equals' or 'exceeds'."
                )
        else:
            raise ValueError("All columns must be integer or floating point.")
    else:
        raise ValueError("Parameter: 'sum': must be > 0")


def distribute_excess(df: pd.DataFrame, subset: str, total: str) -> pd.Series:
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
        # Convert columns to float64 data type for added precision
        # This minimizes floating point errors in scaling
        df[[subset, total]] = df[[subset, total]].astype(np.float64)

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
        raise ValueError("All columns must be integer or floating point.")


def integerize_1d(
    data: np.ndarray | list | pd.Series,
    control: int | float | None = None,
    methodology: str = "weighted_random",
    generator: np.random.Generator | None = None,
) -> np.ndarray:
    """Safe rounding of 1-dimensional array-like structures.

    After some basic input data validation, data is rounded, then rounding error is
    corrected. If input control is zero, the output is also all zero. If input control
    is non-zero but all data is zero, values at the front of the array will be increased
    by one

    Instead of using a basic round, this function instead always rounds up, assuming
    there is any non-zero decimal part. This ensures that when small values (less than
    .5) are passed in, we do not round them down to zero. This greatly helps balance
    and control our tightly restricted data, as simply having values be one instead of
    zero gives us much more flexibility in manual adjustment.

    Args:
        data (np.ndarray | list | pd.Series): An array-like structure of float or
            integer values
        control (int | float | None): Optional control value to scale the input data
            such that the final sum of the elements exactly the control value. If not
            value is provided, then the sum of the input data will be preserved
        methodology (str): How to adjust for rounding error. Defaults to
            "weighted_random". Valid inputs are:
            * "largest": Adjust rounding error by decreasing the largest values until
              the control value is hit
            * "smallest": Adjust rounding error by decreasing the smallest non-zero
              until the control value is hit
            * "largest_difference": Adjust rounding error by decreasing the rounded
              values with the largest change from the original values until the control
              value is hit
            * "weighted_random": Adjust rounding error by decreasing the rounded values
              randomly, with more weight given to those that had a larger change. This
              methodology requires the "generator" parameter to be provided
        generator (np.random.Generator | None): A seeded random generator used to
            select values to change. This is intentionally required from outside the
            function, as if this function created a new seeded generator upon every
            call, it could consistently choose the same categories due to the same
            random state.

    Returns:
        np.ndarray: Integerized data preserving sum or control value

    Raises:
        TypeError: If any of the input variables don't match the correct type
        ValueError: If negative values are encountered in the input variables
        ValueError: If no control value is provided and the input data does not sum to
            an integer
    """
    # Check rounding error methodology
    allowed_methodology = [
        "largest",
        "smallest",
        "largest_difference",
        "weighted_random",
    ]
    if methodology not in allowed_methodology:
        raise ValueError(
            f"Input parameter 'methodology' must be one of {str(allowed_methodology)}"
        )

    # Check a random generator is passed if we are doing "weighted_random"
    if methodology == "weighted_random":
        if generator is None:
            raise ValueError(
                f"Input parameter 'generator' must be provided when the 'methodology' "
                f"is '{methodology}'"
            )
        if type(generator) != np.random.Generator:
            raise ValueError(
                f"Input parameter 'generator' must be of type 'np.random.Generator', "
                f"not {type(generator)}"
            )

    # Check class of input data. If not a np.ndarray, convert to one
    if not isinstance(data, (np.ndarray, list, pd.Series)):
        raise TypeError(
            f"Input parameter 'data' is of type {type(data)}, "
            f"when it must be one of pd.Series, np.ndarray, or list"
        )
    if isinstance(data, list):
        data = np.array(data)
    elif isinstance(data, pd.Series):
        data = data.to_numpy()

    # Confirm no negative values are passed
    if np.any(data < 0):
        raise ValueError("Input parameter 'data' contains negative values")
    if control is not None and control < 0:
        raise ValueError(f"Input parameter 'control' is negative: {control}")

    # If no control provided preserve current sum
    if control is None:
        control = np.sum(data)

    # Ensure control is an integer
    if not math.isclose(control, round(control)):  # type: ignore
        raise ValueError(f"Input parameter 'control' must be integer: {control}")
    else:
        control = int(round(control))  # type: ignore

    # Override if control is zero
    if control == 0:
        data.fill(0)
        return data

    # Override if control is not zero, but all input data is zero
    if control is not None and control != 0 and np.all(data == 0):
        np.add.at(data, np.arange(control), 1)
        return data

    # Scale data to match the control
    unrounded_data = data * control / np.sum(data)

    # Round every value up
    rounded_data = np.ceil(unrounded_data).astype(int)

    # Get difference between control and post-rounding sum.
    # Since data was rounded up, it is guaranteed to be the
    # same or larger than control, making diff non-negative.
    diff = int(np.sum(rounded_data) - control)

    # Adjust values to match difference
    if diff == 0:
        return rounded_data
    else:

        # Find the index values for the n largest data points
        if methodology == "largest":
            to_decrease = np.argsort(rounded_data, stable=True)[-diff:]

        # Find the index values for the n smallest non-zero data points
        elif methodology == "smallest":
            # Find and store all non-zero values/indices
            non_zero_indices = np.flatnonzero(rounded_data)
            non_zero_values = rounded_data[non_zero_indices]

            # Get index values of the n smallest non-zero data points
            n_smallest_non_zero = np.argsort(non_zero_values, stable=True)[:diff]

            # The index values correspond to non_zero_values, not to the original data.
            # Use the reverse lookup to get the indices of the original data
            to_decrease = non_zero_indices[n_smallest_non_zero]

        # Find the index values for the n data points with the largest change after
        # rounding
        elif methodology == "largest_difference":
            rounding_difference = rounded_data - unrounded_data
            to_decrease = np.argsort(rounding_difference, stable=True)[-diff:]

        # Find n random index values weighted on which had the largest change after
        # rounding
        elif methodology == "weighted_random":
            rounding_difference = rounded_data - unrounded_data
            to_decrease = generator.choice(
                a=rounding_difference.size,
                size=diff,
                replace=False,
                p=rounding_difference / rounding_difference.sum(),
            )

        # Decrease n-largest data points by one to match control
        np.add.at(rounded_data, to_decrease, -1)

        # Double check no negatives are present
        if np.any(rounded_data < 0):
            raise ValueError("Negative values encountered in integerized data")

        # Return the data
        return rounded_data.astype(int)


def reallocate_integers(df: pd.DataFrame, subset: str, total: str) -> pd.Series:
    """Adjust subset column such that the columns does not exceed a column
    identified as the total numerical value. Use for positive integer values
    only.

    Args:
        df (pd.DataFrame): Input DataFrame
        subset (str): Column name containing subset of numeric value of
            column identified as the total numerical value
        total (str): Column name containing total numerical value

    Returns:
        pd.Series: Records with excess value re-allocated maintaining
            integer data type
    """
    df = df[[subset, total]].copy()

    # Check columns are integer data types
    if df[subset].dtype.kind != "i" or df[total].dtype.kind != "i":
        raise ValueError("All columns must be integer type.")
    # Ensure columns contain positive values only
    elif (df[subset] < 0).any() or (df[total] < 0).any():
        raise ValueError("Columns must contain only positive values.")
    else:
        # Set condition requiring reallocation
        condition = (df[subset] > df[total]).any()

        # While condition requiring reallocation exists
        while condition:
            # Create Balancer DataFrame
            # Identifying records able to give and records able to receive
            # Including largest differences between total and subset for receivers
            balancer = pd.DataFrame(
                data={
                    "give": df[total] < df[subset],
                    "receive": (df[total] > df[subset]) & (df[subset] > 0),
                    "diff": df[total] - df[subset],
                },
                index=df.index,
            )

            # Number of rows able to be adjusted
            rows = min(balancer["give"].sum(), balancer["receive"].sum())

            # Adjustable rows should be > 0 unless mismatch between subset and total
            if rows > 0:
                # Subtract one from records able to give units
                # Add one to records able to receive units
                # Addition prioritizes records with largest differences
                size = len(balancer.index)
                minuses = [-1 if i < rows else 0 for i in range(size)]
                pluses = [1 if i < rows else 0 for i in range(size)]

                balancer = (
                    balancer.sort_values(by="give", ascending=False)
                    .assign(subtract=minuses)  # type: ignore
                    .sort_values(by=["receive", "diff"], ascending=False)
                    .assign(add=pluses)  # type: ignore
                )

                df = df.join(balancer[["subtract", "add"]])
                df[subset] = df[subset] + df["subtract"] + df["add"]
                df = df.drop(labels=["subtract", "add"], axis=1)

                # Reset condition requiring reallocation
                condition = (df[subset] > df[total]).any()

            else:
                raise ValueError("Cannot Reallocate: Inconsistent Rates or Controls")

        # Return adjusted subset column
        return df[subset]


def reallocate_group_integers(
    df: pd.DataFrame, cols: list[str], total: str
) -> pd.Series:
    """Adjust group of subset columns such that the row-wise values of the
    columns equal the value of the column identified as the total numerical
    value. Use for positive integer values only.

    The sum across all rows within each subset column is preserved excepting
    for cases where preservation is inconsistent with the provided total.

    Args:
        df (pd.DataFrame): Input DataFrame
        cols (list[str]): List of column names
        total (str): Column name containing total numerical value

    Returns:
        pd.Series: Records with excess value re-allocated maintaining
            integer data type
    """
    df = df[[*cols, total]].copy()

    if any(x.kind != "i" for x in df.dtypes.tolist()):
        raise ValueError("All columns must be integer type.")
    # Ensure columns contain positive values only
    elif (df < 0).any().any():
        raise ValueError("Columns must contain only positive values.")
    else:
        # Set condition requiring reallocation
        condition = (df[cols].sum(axis=1) != df[total]).any()
        while condition:
            balancer = pd.DataFrame(
                data={
                    "give": df[cols].sum(axis=1) > df[total],
                    "receive": df[cols].sum(axis=1) < df[total],
                    "col_adj": df[cols].idxmax(axis=1),
                },
                index=df.index,
            )

            # Adjustable rows should be > 0 unless mismatch between subset columns and total
            if min(balancer["give"].sum(), balancer["receive"].sum()) > 0:
                # Subtract one from records able to give units
                # Add one to records able to receive units
                size = len(balancer.index)
                rows = min(balancer["give"].sum(), balancer["receive"].sum())
                minuses = [-1 if i < rows else 0 for i in range(size)]
                pluses = [1 if i < rows else 0 for i in range(size)]
            # If only records are able to give then subtract only
            elif balancer["give"].sum() > balancer["receive"].sum():
                # Subtract one from records able to give units
                # No units are added as no records are able to receive
                size = len(balancer.index)
                rows = balancer["give"].sum()
                minuses = [-1 if i < rows else 0 for i in range(size)]
                pluses = [0 for i in range(size)]
            # If only records are able to receive then add only
            elif balancer["give"].sum() < balancer["receive"].sum():
                # Subtract one from records able to give units
                # No units are added as no records are able to receive
                size = len(balancer.index)
                rows = balancer["receive"].sum()
                minuses = [0 for i in range(size)]
                pluses = [1 if i < rows else 0 for i in range(size)]

            balancer = (
                balancer.sort_values(by="give", ascending=False)
                .assign(subtract=minuses)  # type: ignore
                .sort_values(by="receive", ascending=False)
                .assign(add=pluses)  # type: ignore
            )

            # If there are adjustable rows then
            # Subtraction taken from field with highest value within giving rows
            # While also ensuring balance of +/- within fields
            if min(balancer["give"].sum(), balancer["receive"].sum()) > 0:
                balancer.loc[balancer["add"] > 0, "col_adj"] = balancer[
                    balancer["subtract"] < 0
                ]["col_adj"].tolist()
            # Otherwise add/subtract to/from highest value within rows
            else:
                pass

            for col in cols:
                balancer[col] = np.where(
                    balancer["col_adj"] == col,
                    balancer["add"] + balancer["subtract"],
                    0,
                )

            df = df.join(balancer[cols], rsuffix="_adj")
            for col in cols:
                df[col] = df[col] + df[col + "_adj"]
                df = df.drop(labels=col + "_adj", axis=1)

            # Reset condition requiring reallocation
            condition = (df[cols].sum(axis=1) != df[total]).any()

        # Return adjusted subset columns
        return df[cols]  # type: ignore


def weighted_moving_average(
    x: list[float | int], w: list[float | int]
) -> list[float | int]:
    """Take the weighted moving average of time series records.

    Args:
        x (list[float|int]): The time series records to take a moving average of
        w (list[float|int]): The weighted moving average window and weights

    Returns:
        list[float|int]: The time series records adjusted via the weighted
            moving average
    """
    result = []

    # Adjust weights for records at time series boundary
    w = _adjust_weights(x=x, w=w)  # type: ignore

    # For each record and associated adjusted weights
    for i in range(len(x)):
        # Take the weighted moving average
        cumsum = 0
        for j in range(len(w[i])):  # type: ignore
            if w[i][j] == 0:  # type: ignore
                pass  # 0s may indicate out of time series boundary
            else:
                cumsum += x[i + j - (len(w[i]) // 2)] * w[i][j]  # type: ignore
        result.append(cumsum)

    return result
