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
    with utils.SQL_ENGINE.connect() as connection:
        result = connection.execute(
            sql.text("SELECT COALESCE(MAX([run_id]), 0) AS [id] FROM [metadata].[run]")
        ).scalar()

        return result + 1 if result else 1


def insert_csv(run_id: int, fp: pathlib.Path, tbl: str) -> None:
    """Insert output csv files into database."""
    df = pd.read_csv(fp)
    df["run_id"] = run_id

    with utils.SQL_ENGINE.connect() as connection:
        with connection.begin():
            df.to_sql(
                name=tbl,
                con=connection,
                schema="outputs",
                if_exists="append",
                index=False,
            )


def insert_metadata(
    run_id: int,
    version: str,
    comments: str,
    launch: int,
    horizon: int,
) -> None:
    """Inserts run metadata to the database."""
    with utils.SQL_ENGINE.connect() as connection:
        pd.DataFrame(
            {
                "run_id": run_id,
                "user": getpass.getuser(),
                "date": pd.Timestamp.now(),
                "version": version,
                "comments": comments,
                "loaded": 0,
                "launch": launch,
                "horizon": horizon,
            },
            index=[0],
        ).to_sql(
            name="run",
            con=connection,
            schema="metadata",
            if_exists="append",
            index=False,
        )


def run_etl(launch: int, horizon: int, version: str, comments: str) -> None:
    """Runs the ETL process loading data into the database."""

    # Load the configuration to get the launch and horizon values

    run_id = get_run_id()

    logger.info("Loading output files to database as [run_id]: " + str(run_id))
    insert_metadata(
        run_id=run_id,
        version=version,
        comments=comments,
        launch=launch,
        horizon=horizon,
    )

    output_files = {
        "components": utils.OUTPUT_FOLDER / "components.csv",
        "population": utils.OUTPUT_FOLDER / "population.csv",
        "rates": utils.OUTPUT_FOLDER / "rates.csv",
    }

    for k, v in output_files.items():
        insert_csv(run_id=run_id, fp=v, tbl=k)

    with utils.SQL_ENGINE.connect() as connection:
        with connection.begin():
            connection.execute(
                sql.text(f"UPDATE metadata.run SET loaded = 1 WHERE run_id = {run_id}")
            )
            connection.commit()

    logger.info("Output data loaded to database.")
