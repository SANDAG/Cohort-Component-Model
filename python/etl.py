""" This module runs the ETL process for cohort component model."""

from typing import Dict, Callable
import pandas as pd
import sqlalchemy as sql
from sqlalchemy.orm import Session
from sqlalchemy import insert
import sqlalchemy.engine.base
import yaml
import csv

def load_config(file_path: str) -> dict:
    """Loads configuration from a YAML file."""
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_next_run_id(engine: sqlalchemy.engine.base.Engine, schema: str) -> int:
    """Retrieves the  run_id from the database."""
    query = sql.text(
        f"SELECT COALESCE(MAX(run_id), 0) as max_run_id FROM {schema}.[ccm_run]"
    )
    with engine.connect() as connection:
        result = connection.execute(query).scalar()
        return result + 1 if result else 1

def load_to_sql(
    df: pd.DataFrame, name: str, con: sqlalchemy.engine.base.Engine, schema: str
) -> None:
    """Bulk Loads a DataFrame to a SQL table, handling NULL values."""
    insert_blocks = df.to_dict("records")
    for block in insert_blocks:
        for key, value in block.items():
            if pd.isna(value):
                block[key] = None

    table = sql.Table(
        name,
        sql.MetaData(),
        schema=schema,
        autoload_with=con,
    )

    with Session(con) as session:
        session.execute(insert(table), insert_blocks)
        session.commit()

def run_metadata(run_id: int, version: str, comments: str, engine: sqlalchemy.engine.base.Engine) -> None:
    """Adds run metadata to the [metadata].[ccm_run] table."""
    with engine.connect() as conn:
        result = conn.execute(sql.text("SELECT USER_NAME() as username"))
        user = result.first()[0].split("\\")[1]

    run_metadata = {
        "run_id": run_id,
        "user": user,
        "date": pd.Timestamp.now(),
        "version": version,
        "comments": comments,
        "loaded": 0,
    }
    load_to_sql(
        df=pd.DataFrame([run_metadata]), name="ccm_run", con=engine, schema="metadata"
    )
    print(f"Metadata is loaded.")

def load_data_from_csv(run_id: int, file_path: str, table_name: str, engine: sql.engine.base.Engine) -> None:
    """Loads data from CSV file to SQL"""
    df = pd.read_csv(file_path)
    df['run_id'] = run_id
    load_to_sql(df, table_name, engine, "outputs")

def run_etl(
    config: dict,
    engine: sqlalchemy.engine.base.Engine
) -> None:
    """Runs the ETL process for loading data into SQL"""
    version = config.get('version')
    comments = config.get('comments', None)

    run_id = get_next_run_id(engine, 'metadata')
    run_metadata(run_id, version, comments, engine)

    # Load data for components, population, and rates
    load_data_from_csv(run_id, "output/components.csv", "components", engine)
    print(f"Components data loaded.")
    load_data_from_csv(run_id, "output/population.csv", "population", engine)
    print(f"Population data loaded.")
    load_data_from_csv(run_id, "output/rates.csv", "rates", engine)
    print(f"Rates data loaded.")

    # Update the 'loaded' status to 1 after all ETL tasks are complete
    with engine.connect() as conn:
        sql_command = sql.text(
            f"UPDATE metadata.ccm_run SET loaded = 1 WHERE run_id = {run_id}"
        )
        conn.execute(sql_command)
        conn.commit()
