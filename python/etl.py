"""This module runs the ETL process for cohort component model."""

import getpass
import logging
import pathlib

import pandas as pd
import sqlalchemy as sql

import python.utils as utils

logger = logging.getLogger(__name__)


def get_run_id() -> int:
    """Get the next available run identifier from the database."""
    with utils.CCM_ENGINE.connect() as connection:
        result = connection.execute(
            sql.text("SELECT COALESCE(MAX([run_id]), 0) AS [id] FROM [metadata].[run]")
        ).scalar()

        return result + 1 if result else 1


def insert_csv(run_id: int, fp: pathlib.Path, tbl: str) -> None:
    """Insert output csv files into database."""
    df = pd.read_csv(fp)
    df["run_id"] = run_id

    with utils.CCM_ENGINE.connect() as connection:
        with connection.begin():
            df.to_sql(
                name=tbl,
                con=connection,
                schema="outputs",
                if_exists="append",
                index=False,
            )


def insert_metadata(run_id: int) -> None:
    """Inserts run metadata to the database."""
    with utils.CCM_ENGINE.connect() as connection:
        pd.DataFrame(
            {
                "run_id": run_id,
                "launch": utils.LAUNCH_YEAR,
                "horizon": utils.HORIZON_YEAR,
                "user": getpass.getuser(),
                "start_date": pd.Timestamp.now(),
                "version": utils.VERSION,
                "comments": utils.COMMENTS,
                "complete": 0,
            },
            index=[0],
        ).to_sql(
            name="run",
            con=connection,
            schema="metadata",
            if_exists="append",
            index=False,
        )


def run_etl() -> None:
    """Runs the ETL process loading data into the database."""
    run_id = get_run_id()  # Get the run identifier

    logger.info("Loading output files to database as [run_id]: " + str(run_id))
    insert_metadata(run_id=run_id)

    output_files = {
        "components": utils.OUTPUT_FOLDER / "components.csv",
        "population": utils.OUTPUT_FOLDER / "population.csv",
        "rates": utils.OUTPUT_FOLDER / "rates.csv",
    }

    for k, v in output_files.items():
        insert_csv(run_id=run_id, fp=v, tbl=k)

    with utils.CCM_ENGINE.connect() as connection:
        with connection.begin():
            connection.execute(
                sql.text(
                    "UPDATE [metadata].[run] SET [complete] = 1, "
                    "[end_date] = :end_date WHERE [run_id] = :run_id"
                ),
                {"run_id": run_id, "end_date": pd.Timestamp.now()},
            )

    logger.info("Output data loaded to database.")
