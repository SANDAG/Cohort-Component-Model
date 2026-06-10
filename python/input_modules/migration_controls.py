"""Load optional annual migration controls from CSV."""

import pandas as pd


def get_migration_controls(df: pd.DataFrame) -> dict:
    """Convert migration controls CSV data into yearly control dictionary.

    Expected columns are: year, in, out
    """
    required_cols = {"year", "in", "out"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Migration controls CSV must contain columns: year, in, out")

    controls = {}
    for _, row in df.iterrows():
        if pd.isna(row["year"]):
            raise ValueError("Migration controls CSV contains missing year values")

        year = str(int(row["year"]))
        in_control = row["in"]
        out_control = row["out"]

        controls[year] = {
            "in": None if pd.isna(in_control) else int(in_control),
            "out": None if pd.isna(out_control) else int(out_control),
        }

    return controls
