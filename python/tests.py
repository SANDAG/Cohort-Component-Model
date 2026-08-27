import inspect
import logging
import math
import textwrap
import pandas as pd

logger = logging.getLogger(__name__)


#####################
# HELPFUL CONSTANTS #
#####################

# Within each kind of count, the key is the column name (must exactly match with input
# data) and the value is the exact number of unique values that should be in that
# column
_DISTINCT_COUNTS = {
    "age": 100,
    "race": 7,
    "sex": 2,
    # Different naming convention because fertility only contains one sex (F) and 30 ages (15-44)
    "age_births": 30,
    "sex_births": 1,
}

#########
# TESTS #
#########


def validate_data(table_name: str, data: pd.DataFrame, **kwargs) -> None:
    """Run the specified tests on the input data

    kwargs provides both the name of the test (the name of the keyword argument) and the
    parameters which go into the test (the value of the keyword argument). The exact
    keyword argument names which are allowed are determined by the tests which have been
    implemented in this file. Unless otherwise noted, the string name of the implemented
    tests is the part of the function name after '_validate_'. For example, the string
    name of '_validate_row_count()' is 'row_count'.

    The value of kwargs are the parameters which go into the test, stored in dictionary
    form. The key of the dictionary should be the name of the parameter, while the value
    is the parameter itself. Since every single test requires the 'table_name' and
    'data' parameters, they should not be included in the parameter dictionary. If the
    test requires no additional parameters, an empty dictionary must be passed

    Since kwargs are passed into individual tests, validation is first done to make
    sure each test has all required input arguments. Once validation is passed, all
    requested tests are run

    Args:
        table_name: A descriptive name of the data being tested. Only used when printing
            out error messages
        data: The data to test
        kwargs: The tests to run. The key is the name of the test and the value is a
            dictionary, possibly empty, for the parameters which go into the test

    Raises:
        ValueError: If an error has been encountered relating to the requested test or
            the input parameters to the requested test
        ValueError: Any of the errors raised by the individual tests. See each test
            for additional details
    """
    # I'm sure this is somehow possible to do using Python instead of a hard coded list,
    # but this is just easier
    all_tests = [_validate_row_count, _validate_negative, _validate_null]

    # For each test, get the actual test name by removing the '_validate_'
    all_tests = {test.__name__.replace("_validate_", ""): test for test in all_tests}

    # For the input list of tests, check to make sure that the test exists
    for test_name in kwargs.keys():
        if test_name not in all_tests.keys():
            raise ValueError(
                f"The test '{test_name}' was requested but cannot be found."
            )

    # If test is passed as None, then it is not run and allows explicit disabling of tests
    kwargs = {key: value for key, value in kwargs.items() if value is not None}

    # For each test, make sure that the correct input values are passed
    for test_name, test in all_tests.items():
        if test_name not in kwargs.keys():
            continue

        # Every test requires the 'table_name' and 'data' parameters
        kwargs[test_name]["table_name"] = table_name
        kwargs[test_name]["data"] = data

        # Loop over the parameters for this test
        test_signature = inspect.signature(test)
        for parameter_name, parameter_details in test_signature.parameters.items():

            # If the parameter does not have a default value, then it must be in kwargs
            if parameter_details.default is inspect.Parameter.empty:
                if parameter_name not in kwargs[test_name].keys():
                    raise ValueError(
                        f"The parameter '{parameter_name}' is a required argument for "
                        f"the test '{test_name}' but it is missing"
                    )

            # Check the type of the provided argument, assuming it has been provided
            if parameter_name in kwargs[test_name].keys():

                # Make sure the type of parameter provided to kwargs is correct
                if parameter_details.annotation == set[str]:
                    if type(kwargs[test_name][parameter_name]) != set:
                        raise ValueError(
                            f"The parameter '{parameter_name}' is supposed to be of "
                            f"type 'set[str]' but is instead of type "
                            f"'{type(kwargs[test_name][parameter_name])}'"
                        )
                    if not all(
                        [
                            type(value) == str
                            for value in kwargs[test_name][parameter_name]
                        ]
                    ):
                        raise ValueError(
                            f"The parameter '{parameter_name}' is supposed to be of "
                            f"type 'set[str]' but contains non-string values"
                        )
                else:
                    if (
                        type(kwargs[test_name][parameter_name])
                        != parameter_details.annotation
                    ):
                        raise ValueError(
                            f"The parameter '{parameter_name}' is supposed to be of "
                            f"type '{parameter_details.annotation}' but is actually of "
                            f"type {type(kwargs[test_name][parameter_name])}"
                        )

    # And now we can actually run the tests
    for test_name, test_parameters in kwargs.items():
        all_tests[test_name](**test_parameters)


def _validate_row_count(
    table_name: str,
    data: pd.DataFrame,
    key_columns: set,
) -> None:
    """Verify that the provided data has the correct number of rows

    The correct number of rows is determined by the input 'key_columns', under the
    assumption that input data has functionally the SQL CROSS JOIN of 'key_columns'. The
    number of values in each key column is determined by the variable above labeled
    '_DISTINCT_COUNTS'.

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check. Key columns are determined by the intersection of
            data column names and the columns defined in _DISTINCT_COUNTS
        key_columns: The columns of key values which must be fully represented in the
            data

    Returns:
        True if the row counts of the provided data are valid, False otherwise
    """
    # Verify that the provided key columns actually exist and we have data for them
    for column in key_columns:
        if column not in data.columns:
            raise ValueError(
                f"'{table_name}' is missing the required key column '{column}'"
            )
        if column not in _DISTINCT_COUNTS.keys():
            raise ValueError(
                f"'tests.py' is missing data for the key column '{column}'. Fill in the "
                f"corresponding value in the variable '_DISTINCT_COUNTS'"
            )

    # Collect the number of unique values in each key column
    unique_key_values = {}
    for column in key_columns:
        unique_key_values[column] = _DISTINCT_COUNTS[column]

    # Check that the total number of rows is correct, using the CROSS JOIN of all key columns
    n_rows = math.prod(unique_key_values.values())
    if data.shape[0] != n_rows:
        row_count_explanation = " x ".join(
            [f"{value:,} {column}" for column, value in unique_key_values.items()]
        )
        raise ValueError(
            f"'{table_name}' should have {n_rows} rows ({row_count_explanation}) but "
            f"it has {data.shape[0]}"
        )


def _validate_negative(
    table_name: str, data: pd.DataFrame, negative_ok: set = None
) -> None:
    """Verify that the provided data does not contain negative values

    Checks will be performed on all columns unless they are explicitly passed into the
    function as being allowed to have negative values. Note that the negative value
    check will automatically skip any non-numeric columns

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        negative_ok (optional): Columns where negative values are allowed

    Raises:
        ValueError: When negative values are encountered in columns where they are
            not allowed.
    """
    # Avoid issues with mutable default parameter values
    if negative_ok is None:
        negative_ok = set()

    # Check each column of the input data
    for column in data.columns:

        # Check for negative values except for those columns which are explicitly
        # allowed to be negative
        if column not in negative_ok:
            if pd.api.types.is_numeric_dtype(data[column]) and (data[column] < 0).any():
                # Log the first 5 rows which contain negative values
                logging.debug(
                    (
                        f"'{table_name}' contains negative values in the column '{column}'. "
                        f"Some of the associated rows are:\n"
                        + textwrap.indent(
                            data[data[column] < 0].head(5).to_string(), "\t"
                        )
                    )
                )

                # Raise error and terminate program
                raise ValueError(
                    f"'{table_name}' contains negative values in the column '{column}'. See log for details."
                )


def _validate_null(table_name: str, data: pd.DataFrame, null_ok: set = None) -> None:
    """Verify that the provided data does not contain null values

    Checks will be performed on all columns unless they are explicitly passed into the
    function as being allowed to have null values

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        null_ok (optional): Columns where null values are allowed

    Raises:
        ValueError: When null values are encountered in columns where they are
            not allowed.
    """
    # Avoid issues with mutable default parameter values
    if null_ok is None:
        null_ok = set()

    # Check each column of the input data
    for column in data.columns:

        # Check for null values except for those columns which are explicitly allowed to
        # have null values
        if column not in null_ok:
            if (data[column].isna()).any():
                # Log the first 5 rows which contain null values
                logging.debug(
                    (
                        f"'{table_name}' contains null values in the column '{column}'. "
                        f"Some of the associated rows are:\n"
                        + textwrap.indent(
                            data[data[column].isna()].head(5).to_string(), "\t"
                        )
                    )
                )

                # Raise error and terminate program
                raise ValueError(
                    f"'{table_name}' contains null values in the column '{column}'. See log for details."
                )
