import cerberus
import pathlib
import yaml

import pandas as pd


class InputParser:
    """A class to parse and validate input configurations.

    Attributes:
        _config (dict): The configuration dictionary to be parsed
        base_year (int): Used to store the base year of a new run
        launch_year (int): Used to store the launch year of a new run
        horizon_year (int): Used to store the horizon year of a new run
        version (str): The software version of the current run
        comments (str): Any comments associated with the current run
        controls (dict): Mapping of control totals for each year
        migration_controls (pd.DataFrame | None): Optional migration control totals (ins/outs)
            for each post-launch increment year. If not provided, set to None.
        mortality_controls (pd.DataFrame | None): Optional mortality rates by
            race, sex, and age. If not provided, set to None.
        load_to_database (bool): Whether to load the run results into a database.

    Methods:
        parse_config(): Control function
        _validate_config(): Validate the configuration file
        _parse_years(): Parses the run launch and horizon years from the configuration
            file and sets the base year
        _parse_controls(): Parses the controls mapping from the configuration file and
            sets the controls attribute
        _parse_migration_controls(): Parses the migration controls mapping from the
            configuration file and sets the migration_controls attribute
        _parse_mortality_controls(): Parses the mortality rate controls from the
            configuration file and sets the mortality_controls attribute
    """

    def __init__(self, config: dict) -> None:
        """Initialize the InputParser with a configuration dictionary."""
        self._config = config
        self.base_year = None
        self.launch_year = None
        self.horizon_year = None
        self.version = None
        self.comments = None
        self.controls = {}
        self.migration_controls = None
        self.mortality_controls = None
        self.mortality_forecast_year = None
        self.load_to_database = None

    def parse_config(self) -> None:
        """Control flow to parse the runtime configuration.

        First, the contents of the configuration file are validated. Then, the
        base, launch, and horizon years are set along with the software version
        and any comments. Finally, the controls totals and optional migration control totals are parsed and set.
        """
        self._validate_config()
        _interval = self._parse_interval()
        self.base_year = _interval["base_year"]
        self.launch_year = _interval["launch_year"]
        self.horizon_year = _interval["horizon_year"]
        self.comments = self._config.get("comments")
        self.version = self._config.get("version")
        self.controls = self._parse_controls()
        self.migration_controls = self._parse_migration_controls()
        self.mortality_forecast_year = self._config.get("csv", {}).get(
            "mortality_forecast_year", None
        )
        self.mortality_controls = self._parse_mortality_controls()
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
                    "controls": {"type": "string"},
                },
            },
            "csv": {
                "type": "dict",
                "schema": {
                    "migration_controls": {"type": "string", "nullable": True},
                    "mortality_controls": {"type": "string", "nullable": True},
                    "mortality_forecast_year": {
                        "type": "integer",
                        "nullable": True,
                    },
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
        """Parse the base, launch, and horizon years from the configuration file."""
        launch_year = self._config["interval"]["launch"]
        horizon_year = self._config["interval"]["horizon"]

        # Ensure launch year is less than horizon year
        if launch_year >= horizon_year:
            raise ValueError("Launch year must be less than horizon year")

        if 2020 <= launch_year <= 2029:
            base_year = 2020
        else:
            raise ValueError("""
                    Only base year 2020 is supported at this time.
                    Launch year must be between 2020 and 2029.
                """)

        return {
            "base_year": base_year,
            "launch_year": launch_year,
            "horizon_year": horizon_year,
        }

    def _parse_controls(self) -> dict:
        """Parse the controls mapping from the configuration file."""
        # Check the controls mapping file exists and is a valid YAML file
        controls_fp = self._config["configurations"]["controls"]
        controls_path = pathlib.Path(controls_fp)
        if not controls_path.is_absolute():
            controls_path = (
                pathlib.Path(__file__).resolve().parent.parent / controls_path
            )
        try:
            with open(controls_path, "r") as f:
                controls = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Controls file not found: {controls_fp}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing controls YAML file: {e}")

        # TODO: Normally we would validate the schema but this is soon to be removed.

        return controls

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

    def _parse_mortality_controls(self) -> pd.DataFrame | None:
        """Parse the mortality controls CSV file from the configuration file.

        The CSV file must contain mortality rates by race, sex, age, and year.

        Returns:
            pd.DataFrame | None: DataFrame with columns (race, sex, age, year, rate_death),
                or None if no file is provided.
        """
        # Check if mortality controls file is provided
        mortality_controls_fp = self._config["csv"].get("mortality_controls")
        if mortality_controls_fp is None:
            return None

        mortality_controls_path = pathlib.Path(mortality_controls_fp)
        if not mortality_controls_path.is_absolute():
            mortality_controls_path = (
                pathlib.Path(__file__).resolve().parent.parent / mortality_controls_path
            )
        try:
            with open(mortality_controls_path, "r") as f:
                mortality_controls = pd.read_csv(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Mortality controls file not found: {mortality_controls_fp}"
            )
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing mortality controls CSV file: {e}")

        # Ensure DataFrame contains required columns
        required_cols = {"race", "sex", "age", "year", "rate_death"}
        if not required_cols.issubset(mortality_controls.columns):
            raise ValueError(
                "Mortality controls must contain columns: (race, sex, age, year, rate_death)"
            )

        # Check mortality rates are >= 0 and <= 1
        if any(mortality_controls["rate_death"] < 0) or any(
            mortality_controls["rate_death"] > 1
        ):
            raise ValueError("Mortality rates must be between 0 and 1")

        # Check for duplicate race/sex/age/year combinations
        if mortality_controls.duplicated(subset=["race", "sex", "age", "year"]).any():
            raise ValueError(
                "Duplicate race/sex/age/year combinations found in mortality controls"
            )

        # Check age range is valid (0-99)
        if any(mortality_controls["age"] < 0) or any(mortality_controls["age"] > 99):
            raise ValueError("Age values must be between 0 and 99")

        # Validate year column
        control_years = set(mortality_controls["year"].unique())

        # If mortality_forecast_year is specified, only validate that year exists
        if self.mortality_forecast_year is not None:
            if self.mortality_forecast_year not in control_years:
                available_years = sorted(control_years)
                raise ValueError(
                    f"mortality_forecast_year ({self.mortality_forecast_year}) not found in mortality controls. "
                    f"Available years: {available_years[0]}-{available_years[-1]}"
                )
        else:
            # If no forecast year specified, require all post-launch years (year-by-year mode)
            post_launch_years = range(self.launch_year + 1, self.horizon_year + 1)  # type: ignore
            missing_years = set(post_launch_years) - control_years

            if missing_years:
                raise ValueError(
                    f"Missing required years in mortality rate controls: {sorted(missing_years)}. "
                    f"Required years: {list(post_launch_years)}"
                )

        return mortality_controls
