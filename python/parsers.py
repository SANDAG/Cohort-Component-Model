import cerberus
import logging
import pathlib

import pandas as pd
import sqlalchemy as sql

import python.tests as tests

logger = logging.getLogger(__name__)


class InputParser:
    """A class to parse and validate input configurations.

    Attributes:
        _config (dict): The configuration dictionary to be parsed
        _engine (sql.Engine): The SQL engine which corresponds to the Estimates Program database
        launch_year (int): Used to store the launch year of a new run
        horizon_year (int): Used to store the horizon year of a new run
        version (str): The software version of the current run
        comments (str): Any comments associated with the current run
        estimates_run_id (int): The run ID for the Estimates Program launch year run
        migration_controls (pd.DataFrame | None): Optional migration control totals (ins/outs)
            for each post-launch increment year. If not provided, set to None.
        mortality_rates (pd.DataFrame | None): Optional mortality rates by
            age, sex, and race. If not provided, set to None.
        fertility_rates (pd.DataFrame | None): Optional fertility rates by
            race, sex, and age. If not provided, set to None.
        load_to_database (bool): Whether to load the run results into a database.

    Methods:
        parse_config(): Control function
        _validate_config(): Validate the configuration file
        _parse_years(): Parses the run launch and horizon years
        _parse_estimates_run_id(): Parses the Estimates Program run ID from the
            configuration file and sets the estimates_run_id attribute
        _parse_migration_controls(): Parses the migration controls mapping from the
            configuration file and sets the migration_controls attribute
        _parse_mortality_rates(): Parses the mortality rate controls from the
            configuration file and sets the mortality_rates attribute
        _parse_fertility_rates(): Parses the fertility rate controls from the
            configuration file and sets the fertility_rates attribute
    """

    def __init__(self, config: dict, engine: sql.Engine) -> None:
        """Initialize the InputParser with a configuration dictionary."""
        self._config = config
        self._engine = engine
        self.launch_year = None
        self.horizon_year = None
        self.version = None
        self.comments = None
        self.estimates_run_id = None
        self.migration_controls = None
        self.mortality_rates = None
        self.fertility_rates = None
        self.load_to_database = None

    def parse_config(self) -> None:
        """Control flow to parse the runtime configuration.

        First, the contents of the configuration file are validated. Then, the
        launch and horizon years are set along with the software version and
        any comments. Finally, the controls totals and optional migration
        control totals are parsed and set.
        """
        self._validate_config()
        _interval = self._parse_interval()
        self.launch_year = _interval["launch_year"]
        self.horizon_year = _interval["horizon_year"]
        self.comments = self._config.get("comments")
        self.version = self._config.get("version")
        self.estimates_run_id = self._parse_estimates_run_id()
        self.migration_controls = self._parse_migration_controls()
        self.mortality_rates = self._parse_mortality_rates()
        self.fertility_rates = self._parse_fertility_rates()
        self.load_to_database = self._config.get("sql", {}).get(
            "load_to_database", False
        )

    def _validate_config(self) -> None:
        """Validate the contents of the configuration dictionary."""
        # Check all keys are present and key types using Cerberus. For help, see their
        # website here: https://docs.python-cerberus.org/usage.html
        schema = {
            "version": {"type": "string", "allowed": ["0.0.0-dev"]},
            "comments": {"type": "string"},
            "configurations": {
                "type": "dict",
                "schema": {
                    "estimates_run_id": {"type": "integer"},
                },
            },
            "csv": {
                "type": "dict",
                "schema": {
                    "migration_controls": {"type": "string", "nullable": True},
                    "mortality_rates": {"type": "string", "nullable": True},
                    "fertility_rates": {"type": "string", "nullable": True},
                },
            },
            "interval": {
                "type": "dict",
                "schema": {
                    "launch": {"type": "integer", "min": 2010, "max": 2025},
                    "horizon": {"type": "integer", "min": 2011},
                },
            },
            "sql": {
                "type": "dict",
                "schema": {"load_to_database": {"type": "boolean"}},
            },
        }

        validator = cerberus.Validator(schema, require_all=True)
        if not validator.validate(self._config):
            raise ValueError(validator.errors)

    def _parse_interval(self) -> dict:
        """Parse the launch, and horizon years from the configuration file."""
        launch_year = self._config["interval"]["launch"]
        horizon_year = self._config["interval"]["horizon"]

        # Ensure launch year is less than horizon year
        if launch_year >= horizon_year:
            raise ValueError("Launch year must be less than horizon year")

        if launch_year < 2010 or launch_year > 2025:
            raise ValueError("Launch years must be between 2010 and 2025")

        return {
            "launch_year": launch_year,
            "horizon_year": horizon_year,
        }

    def _parse_estimates_run_id(self) -> None:
        """Check if supplied Estimates Program run id is valid."""
        estimates_run_id = self._config["configurations"].get("estimates_run_id")

        with self._engine.connect() as con:
            # Ensure supplied run id exists in the Estimates Program database
            # And that is complete and contains the launch year
            query = sql.text("""
                    SELECT CASE WHEN EXISTS (
                        SELECT [run_id]
                        FROM [metadata].[run]
                        WHERE [run_id] = :run_id
                            AND [complete] = 1
                            AND :year BETWEEN [start_year] AND [end_year]
                    ) THEN 1 ELSE 0 END
                """)

            exists = con.execute(
                query, {"run_id": estimates_run_id, "year": self.launch_year}
            ).scalar()
            if exists == 0:
                raise ValueError(
                    f"Either the [run_id]={estimates_run_id} does not exist in the database or "
                    f"it is not marked as [complete]=1 or it does not contain the provided "
                    f"launch year={self.launch_year}"
                )
            else:
                return estimates_run_id

    def _parse_migration_controls(self) -> pd.DataFrame | None:
        """Parse the migration controls CSV file from the configuration file."""
        # Check the migration controls file exists and is a valid CSV file
        migration_controls_fp = self._config["csv"].get("migration_controls")
        if migration_controls_fp is None:
            return None

        migration_controls_path = pathlib.Path(migration_controls_fp)
        if not migration_controls_path.is_absolute():
            migration_controls_path = (
                pathlib.Path(__file__).resolve().parent.parent / migration_controls_path
            )
        try:
            with open(migration_controls_path, "r") as f:
                migration_controls = pd.read_csv(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Migration controls file not found: {migration_controls_fp}"
            )
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing migration controls CSV file: {e}")

        # Ensure DataFrame contains required columns
        required_cols = {"year", "ins", "outs"}
        if not required_cols.issubset(migration_controls.columns):
            raise ValueError(
                "Migration controls must contain columns: (year, ins, outs)"
            )

        # Check control totals are >= 0
        if any(migration_controls["ins"] < 0) or any(migration_controls["outs"] < 0):
            raise ValueError("Migration control totals must be >= 0")

        # Check for duplicate years in migration controls
        if migration_controls["year"].duplicated().any():
            raise ValueError("Duplicate years found in migration controls")

        # Check that all years in migration controls are post-launch years
        post_launch_years = range(self.launch_year + 1, self.horizon_year + 1)  # type: ignore
        if not all(year in post_launch_years for year in migration_controls["year"]):
            raise ValueError("Migration controls must only contain post-launch years")

        # Check that all post-launch years are present in migration controls
        if not all(
            year in migration_controls["year"].values for year in post_launch_years
        ):
            raise ValueError("Migration controls must contain all post-launch years")

        return migration_controls

    def _parse_mortality_rates(self) -> pd.DataFrame | None:
        """Parse the mortality rates CSV file from the configuration file.

        The CSV file must contain mortality rates by year, age, sex, and race.

        Returns:
            pd.DataFrame | None: DataFrame with columns (year, age, sex, race, rate_death),
                or None if no file is provided.
        """
        # Check if mortality rates file is provided
        mortality_rates_fp = self._config["csv"].get("mortality_rates")
        if mortality_rates_fp is None:
            return None

        mortality_rates_path = pathlib.Path(mortality_rates_fp)
        if not mortality_rates_path.is_absolute():
            mortality_rates_path = (
                pathlib.Path(__file__).resolve().parent.parent / mortality_rates_path
            )
        try:
            with open(mortality_rates_path, "r") as f:
                mortality_rates = pd.read_csv(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Mortality rates file not found: {mortality_rates_fp}"
            )
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing mortality rates CSV file: {e}")

        # Ensure DataFrame contains required columns
        required_cols = {"year", "age", "sex", "race", "rate_death"}
        if not required_cols.issubset(mortality_rates.columns):
            raise ValueError(
                "Mortality rates must contain columns: (year, age, sex, race, rate_death)"
            )

        # Required mortality-control fields cannot be null
        if mortality_rates[list(required_cols)].isna().any().any():
            raise ValueError("Mortality rates must not contain null values")

        # Check mortality rates are > 0 and < 1
        if any(mortality_rates["rate_death"] < 0) or any(
            mortality_rates["rate_death"] > 1
        ):
            raise ValueError("Mortality rates must be greater than 0 and less than 1")

        # Check for duplicate year/age/sex/race combinations
        if mortality_rates.duplicated(subset=["year", "age", "sex", "race"]).any():
            raise ValueError(
                "Duplicate year/age/sex/race combinations found in mortality rates"
            )

        # Check age range is valid (0-99)
        if any(mortality_rates["age"] < 0) or any(mortality_rates["age"] > 99):
            raise ValueError("Age values must be between 0 and 99")

        # Validate year column - require all post-launch years (year-by-year mode)
        control_years = set(mortality_rates["year"].unique())
        post_launch_years = range(self.launch_year + 1, self.horizon_year + 1)  # type: ignore
        missing_years = set(post_launch_years) - control_years

        if missing_years:
            raise ValueError(
                f"Missing required years in mortality rates: {sorted(missing_years)}. "
                f"Required years: {list(post_launch_years)}"
            )

        # Validate each year has the correct structure
        for year in mortality_rates["year"].unique():
            year_data = mortality_rates[mortality_rates["year"] == year]
            tests.validate_data(
                table_name=f"Mortality Rates (year {year})",
                data=year_data[["race", "sex", "age", "rate_death"]],
                row_count={"key_columns": {"race", "sex", "age"}},
                negative={"negative_ok": set()},
                null={"null_ok": set()},
            )

        return mortality_rates

    def _parse_fertility_rates(self) -> pd.DataFrame | None:
        """Parse the fertility rates CSV file from the configuration file.

        The CSV file must contain fertility rates by year, age, sex, and ethnicity.

        Returns:
            pd.DataFrame | None: DataFrame with columns (year, age, sex, ethnicity, rate_birth),
                or None if no file is provided.
        """
        # Check if fertility rate file is provided
        fertility_rates_fp = self._config["csv"].get("fertility_rates")
        if fertility_rates_fp is None:
            return None

        fertility_rates_path = pathlib.Path(fertility_rates_fp)
        if not fertility_rates_path.is_absolute():
            fertility_rates_path = (
                pathlib.Path(__file__).resolve().parent.parent / fertility_rates_path
            )
        try:
            with open(fertility_rates_path, "r") as f:
                fertility_rates = pd.read_csv(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Fertility rate file not found: {fertility_rates_fp}"
            )
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing fertility rate CSV file: {e}")

        # Ensure DataFrame contains required columns
        required_cols = {"year", "age", "sex", "ethnicity", "rate_birth"}
        if not required_cols.issubset(fertility_rates.columns):
            raise ValueError(
                "Fertility rates must contain columns: "
                "(year, age, sex, ethnicity, rate_birth)"
            )

        # Check fertility rates are > 0 and < 1
        if any(fertility_rates["rate_birth"] < 0) or any(
            fertility_rates["rate_birth"] > 1
        ):
            raise ValueError("Fertility rates must be greater than 0 and less than 1")

        # Check fertility sex is only Female
        if not all(fertility_rates["sex"] == "Female"):
            raise ValueError("Fertility rates must be for females only")

        # Check age range is valid (15-44)
        if any(fertility_rates["age"] < 15) or any(fertility_rates["age"] > 44):
            raise ValueError("Age values must be between 15 and 44")

        # Validate year column
        control_years = set(fertility_rates["year"].unique())
        post_launch_years = range(self.launch_year + 1, self.horizon_year + 1)  # type: ignore
        missing_years = set(post_launch_years) - control_years

        if missing_years:
            raise ValueError(
                f"Missing required years in fertility rates: {sorted(missing_years)}. "
                f"Required years: {list(post_launch_years)}"
            )

        # Validate each year has the correct structure
        for year in fertility_rates["year"].unique():
            year_data = fertility_rates[fertility_rates["year"] == year]
            tests.validate_data(
                table_name=f"Birth Rates (year {year})",
                # Rename age column for test (birth data only 15-44)
                data=year_data[["age", "ethnicity", "rate_birth"]].rename(
                    columns={"age": "age_births"}
                ),
                row_count={"key_columns": {"ethnicity", "age_births"}},
                negative={"negative_ok": set()},
                null={"null_ok": set()},
            )

        return fertility_rates[["year", "age", "sex", "ethnicity", "rate_birth"]]
