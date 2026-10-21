import sklearn

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.input_modules.birth_rates as birth_rates
import python.input_modules.death_rates as death_rates
import python.input_modules.launch_year as launch_year
import python.utils as utils


def _calculate_fertility_rates(year: int) -> pd.DataFrame:
    """Calculate fertility rates for each year.

    Reconstructs single-year-of-age fertility rates for a
    given year by delegating to the lower-level helpers in
    `python/input_modules/birth_rates.py`.
    """
    inputs = birth_rates._get_fertility_inputs(year)
    birth_rates._validate_fertility_inputs(inputs["fertility_inputs"])

    outputs = birth_rates._create_fertility_outputs(inputs)
    birth_rates._validate_fertility_outputs(outputs)

    return outputs


def _get_population_estimates(year: int) -> pd.DataFrame:
    """Fetch SANDAG Estimates Program population for an arbitrary year.

    Mirrors launch_year.run_launch_year(), but parameterized by year instead of
    being hardcoded to utils.LAUNCH_YEAR, since historical reconstruction needs
    population for 2022, 2023, and 2024.
    """
    with utils.CCM_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "launch" / "get_ase_distribution.sql") as file:
            dof_ase = pd.read_sql_query(
                sql.text(file.read()), connection, params={"year": year}
            )

    with utils.ESTIMATES_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "launch" / "get_estimates_ase.sql") as file:
            estimates = pd.read_sql_query(
                sql.text(file.read()),
                connection,
                params={"run_id": utils.ESTIMATES_RUN_ID, "year": year},
            )

    launch_inputs = {"dof_ase": dof_ase, "estimates": estimates}
    launch_year._validate_launch_inputs(launch_inputs)

    population = launch_year._create_launch_outputs(launch_inputs)
    launch_year._validate_launch_outputs(population)

    return population


def _calculate_mortality_rates(year: int) -> pd.DataFrame:
    """Calculate mortality rates for each year.

    Reconstructs single-year-of-age mortality rates for a
    given year by delegating to the lower-level helpers in
    `python/input_modules/death_rates.py`.
    """
    # San Diego County population is suppressed in CDC WONDER for 2018+ (year >= 2022),
    population = _get_population_estimates(year) if year >= 2022 else None

    inputs = death_rates._get_mortality_inputs(year, population=population)
    death_rates._validate_mortality_inputs(
        inputs["mortality_inputs"], inputs["undesa_rates"]
    )

    outputs = death_rates._create_mortality_outputs(inputs)
    death_rates._validate_mortality_outputs(outputs)

    return outputs


class LeeCarterModel(sklearn.base.BaseEstimator, sklearn.base.RegressorMixin):
    """
    Custom Lee-Carter model using precomputed expanding window splits.

    This model expects data for a single (race/ethnicity, sex) group at a time.

    Attributes:
        phi (float | None): Optional decay parameter for certain decay methods.
            Only None or a float value is allowed. Defaults to None.
        forecast_ (pd.DataFrame): Forecasted rates (years × ages).

    Methods:
        fit(X: pd.DataFrame, y: pd.Series) -> 'LeeCarterModel':
            Fits the Lee-Carter model and forecasts future rates.
        predict(X: pd.DataFrame) -> np.ndarray:
            Predicts rates for each row using the forecasted values.
    """

    def __init__(
        self,
        phi: float | None = None,
    ):
        """
        Initialize LeeCarterModel.

        Args:
            phi (float | None, optional): Decay parameter for certain decay methods.
                Defaults to None.
        """
        if phi is not None and not isinstance(phi, float):
            raise ValueError("phi must be None or a float.")

        self.phi = phi
        self.forecast_: pd.DataFrame

    def fit(
        self, X: pd.DataFrame, y: pd.Series, forecast_year: int | None = None
    ) -> "LeeCarterModel":
        """
        Fit the Lee-Miller model for each (race/ethnicity, sex) group and forecast
        future rates.

        Args:
            X (pd.DataFrame): Feature DataFrame.
            y (pd.Series): Target rates.
            forecast_year (int | None, optional): Year to forecast. If None, use the
                last year in X.

        Returns:
            LeeCarterModel: Fitted model.
        """
        # Validate inputs
        if "year" not in X.columns or "age" not in X.columns:
            raise ValueError("X must contain 'year' and 'age' columns")

        if len(X) != len(y):
            raise ValueError("X and y must have the same length")

        last_year = int(X["year"].max())
        first_year = int(X["year"].min())

        if forecast_year is None:
            steps = last_year - first_year
        else:
            steps = forecast_year - last_year
            if steps < 1:
                raise ValueError(
                    "forecast_year must be after the last year in training data."
                )

        mtx = X[["year", "age"]].copy()
        mtx["rates"] = y.values

        mtx = mtx.pivot(index="age", columns="year", values="rates")

        # Log rates
        log_mx = np.log(mtx)
        log_mx = pd.DataFrame(log_mx, index=mtx.index, columns=mtx.columns)

        # Compute a_x
        a_x = log_mx.mean(axis=1)

        # Center the matrix
        centered = log_mx.sub(a_x, axis=0)

        # Calculate SVD
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)

        # Extract components
        b_x = U[:, 0]
        k_t = S[0] * Vt[0, :]

        # If sum(b_x) < 0, flip signs
        if b_x.sum() < 0:
            b_x = -b_x
            k_t = -k_t

        # Normalize
        b_x_sum = b_x.sum()
        b_x /= b_x_sum
        k_t *= b_x_sum

        # Ensure b_x, k_t are series with correct indices
        b_x = pd.Series(b_x, index=mtx.index)
        start_year = int(mtx.columns[0])
        k_t = pd.Series(
            k_t,
            index=pd.RangeIndex(start=start_year, stop=start_year + len(k_t)),
        )

        # Estimate drift
        # In the original Lee-Carter paper, k_t is modeled as a random walk with
        #   constant drift:
        #     k_t = k_{t-1} + drift + noise
        # This is equivalent to an ARIMA(0,1,0) with drift, where the only parameter
        # requiring estimation is the constant drift. The standard approach is to
        # estimate the drift as the mean of the first-order differences of k_t.
        # While the Lee-Carter paper mentions ARIMA(0,1,0), here we do not fit a
        # full ARIMA model because:
        #   - The random walk with drift can be modeled simply
        #   - The drift parameter can be directly estimated as the mean of
        #   np.diff(k_t)
        #   - This avoids unnecessary model fitting and is computationally efficient
        drift = np.mean(np.diff(k_t))

        self.a_x, self.b_x, self.k_t, self.drift, self.last_year, self.last_k_t = (
            a_x,
            b_x,
            k_t,
            drift,
            int(X["year"].max()),
            k_t.iloc[-1],
        )

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict rates for each row using the forecasted values.

        Args:
            X (pd.DataFrame): Feature DataFrame with 'year' and 'age' columns.

        Returns:
            np.ndarray: Predicted rates.

        Raises:
            ValueError: If model is not fitted or required columns are missing.
        """
        # Check if model is fitted
        if not hasattr(self, "a_x"):
            raise ValueError("Model must be fitted before calling predict")

        required_cols = ["year", "age"]
        missing_cols = [col for col in required_cols if col not in X.columns]
        if missing_cols:
            raise ValueError(f"X must contain columns: {missing_cols}")

        preds = []

        for _, row in X.iterrows():
            age = int(row["age"])
            n_steps = row["year"] - self.last_year
            if self.phi is not None:
                drift_sum = sum(
                    self.drift * (self.phi**i) for i in range(1, n_steps + 1)
                )
                k_t_pred = self.last_k_t + drift_sum
            else:
                k_t_pred = self.last_k_t + self.drift * n_steps

            log_mx = self.a_x.loc[age] + self.b_x.loc[age] * k_t_pred
            preds.append(np.exp(log_mx))

        return np.array(preds)


def generate_rate_forecast(
    df: pd.DataFrame,
    rate_col: str,
    forecast_start_year: int,
    forecast_end_year: int,
    phi: float = 0.8,
    output_path: str | None = None,
) -> pd.DataFrame:
    """
    Generate rate forecasts using the Lee-Carter model.

    Args:
        df (pd.DataFrame): A DataFrame of historical rates (must include
            'age', 'sex', 'race', and a rate column).
        rate_col (str): Name of the rate column being forecast (e.g. "rate_birth" or
            "rate_death").
        forecast_start_year (int): First year to forecast.
        forecast_end_year (int): Final year to forecast.
        phi (float, optional): Phi parameter for the Lee-Carter model (default: 0.8).
        output_path (str | None, optional): Path where the forecast CSV will be
            saved. If None, the forecast is not saved.

    Returns:
        pd.DataFrame: Forecasted rates by year, age, sex, and race.
    """
    model = LeeCarterModel(phi=phi)

    # Generate forecasts for each demographic group
    forecast_results = []
    future_years = list(range(forecast_start_year, forecast_end_year + 1))

    for sex in df["sex"].unique():
        for ethnicity in df["ethnicity"].unique():
            # Fit model for each sex/ethnicity group (across all ages)
            mask = (df["sex"] == sex) & (df["ethnicity"] == ethnicity)
            train_data = df.loc[mask].copy()

            # Fit on historical data
            model.fit(
                train_data[["year", "age"]],
                train_data[rate_col],
                forecast_year=forecast_end_year,
            )

            # Create future predictions for all ages
            for age in df["age"].unique():
                future_data = pd.DataFrame(
                    {
                        "year": future_years,
                        "age": age,
                        "sex": sex,
                        "ethnicity": ethnicity,
                    }
                )
                future_data[rate_col] = model.predict(future_data)
                forecast_results.append(future_data)

    df_forecast = pd.concat(forecast_results, ignore_index=True)

    if output_path is not None:
        df_forecast.to_csv(output_path, index=False)

    return df_forecast
