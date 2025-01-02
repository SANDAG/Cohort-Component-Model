""" This module runs the ETL process for cohort component model."""

import getpass
import logging
import pandas as pd
import sqlalchemy as sql

logger = logging.getLogger(__name__)
    
def get_run_id(engine: sql.Engine) -> int:
    """Get the next available run identifier from the database."""
    with engine.connect() as connection:
        result = connection.execute(
            sql.text("SELECT COALESCE(MAX([run_id]), 0) AS [id] FROM [metadata].[run]")
        ).scalar()

        return result + 1 if result else 1


def insert_csv(engine: sql.Engine, run_id: int, fp: str, tbl: str) -> None:
    """Insert output csv files into database."""
    df = pd.read_csv(fp)
    df["run_id"] = run_id

    with engine.connect() as connection:
        with connection.begin():
            df.to_sql(
                name=tbl,
                con=connection,
                schema="outputs",
                if_exists="append",
                index=False,
            )


def insert_metadata(
    engine: sql.Engine,
    run_id: int,
    version: str,
    comments: str,
    launch: int,
    horizon: int
) -> None:
    """Inserts run metadata to the database."""
    with engine.connect() as connection:
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


def run_etl(engine: sql.Engine, launch: int, horizon: int, version: str, comments: str) -> None:
    """Runs the ETL process loading data into the database."""
    
    # Load the configuration to get the launch and horizon values

    run_id = get_run_id(engine=engine)

    logger.info("Loading output files to database as [run_id]: " + str(run_id))
    insert_metadata(engine=engine, run_id=run_id, version=version, comments=comments, launch=launch, horizon=horizon)

    output_files = {
        "components": "output/components.csv",
        "population": "output/population.csv",
        "rates": "output/rates.csv",
    }

    for k, v in output_files.items():
        insert_csv(engine=engine, run_id=run_id, fp=v, tbl=k)

    with engine.connect() as connection:
        with connection.begin():
            connection.execute(
                sql.text(f"UPDATE metadata.run SET loaded = 1 WHERE run_id = {run_id}")
            )
            connection.commit()

    logger.info("Output data loaded to database.")