import sklearn

import numpy as np
import pandas as pd

import python.input_modules.death_rates as death_rates
import python.input_modules.launch_year as launch_year


def get_mortality_rates(year: int) -> pd.DataFrame:
    """Calculate single-year-of-age mortality rates for a given year."""
    population = None
    if year >= 2022:
        launch_inputs = launch_year._get_launch_inputs(year)
        launch_year._validate_launch_inputs(launch_inputs)

        population = launch_year._create_launch_outputs(launch_inputs)
        launch_year._validate_launch_outputs(population)

    mortality_inputs = death_rates._get_mortality_inputs(year, population=population)
    death_rates._validate_mortality_inputs(
        mortality_inputs["mortality_inputs"], mortality_inputs["undesa_rates"]
    )

    mortality_outputs = death_rates._create_mortality_outputs(mortality_inputs, year)
    death_rates._validate_mortality_outputs(mortality_outputs)

    return mortality_outputs


class LeeCarterModel(sklearn.base.BaseEstimator, sklearn.base.RegressorMixin):
    """Custom Lee-Carter model.

    The Lee-Carter Model is a statistical framework for forecasting mortality rates over
    time. The model assumes that the mortality rate at a given age and time
    can be represented as the sum of three components: the typical pattern of mortality
    across ages, an overall mortality trend over time, and how strongly each age responds
    to that trend.

    We use this model to project mortality rates for each age and sex combination in
    future years, and as such this model expects data for a single (sex, race/ethnicity)
    group at a time.

    Attributes:
        phi (float | None): Optional decay parameter. Defaults to None.
        fitted (bool): Indicates whether the model has been fitted
        a_x (pd.Series | None): Age-specific average log rates after fitting
        b_x (pd.Series | None): Age-specific sensitivity to the time index after fitting
        k_t (pd.Series | None): Time index capturing overall level of mortality after fitting
        drift (float | None): Estimated drift of the time index after fitting
        last_year (int | None): Last observed year in the training data
        last_k_t (float | None): Value of k_t in the last observed year

    Methods:
        fit(X: pd.DataFrame, y: pd.Series) -> 'LeeCarterModel':
            Fits the Lee-Carter model
        predict(X: pd.DataFrame) -> np.ndarray: Predicts rates for each row
    """

    def __init__(self, phi: float | None = None) -> None:
        """Initialize LeeCarterModel.

        Args:
            phi (float | None): Optional decay parameter. Defaults to None.
        """
        if phi is not None and not isinstance(phi, float):
            raise ValueError("phi must be None or a float.")

        self.phi = phi
        self.fitted = False
        self.a_x = None
        self.b_x = None
        self.k_t = None
        self.drift = None
        self.last_year = None
        self.last_k_t = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LeeCarterModel":
        """Fit the Lee-Carter model.

        Fitting estimates the following components from the historical rates,
        which `predict` uses later:
            a_x: Age-specific average log rates
            b_x: Age-specific sensitivity to the time index
            k_t: Time index capturing overall level of mortality
            drift: Estimated drift of the time index
            last_year: Last observed year in the training data
            last_k_t: Value of k_t in the last observed year

        Args:
            X (pd.DataFrame): Feature DataFrame
            y (pd.Series): Target rates

        Returns:
            LeeCarterModel: Fitted model
        """
        # Validate inputs
        if "year" not in X.columns or "age" not in X.columns:
            raise ValueError("X must contain 'year' and 'age' columns")

        if len(X) != len(y):
            raise ValueError("X and y must have the same length")

        mtx = (
            X[["year", "age"]]
            .assign(rates=np.log(y.values))  # Log-transform the rates before pivoting
            .pivot(index="age", columns="year", values="rates")
        )

        # Compute a_x
        a_x = mtx.mean(axis=1)

        # Center the matrix
        centered = mtx.sub(a_x, axis=0)

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
        #   - The drift parameter can be directly estimated as the mean of np.diff(k_t)
        #   - This avoids unnecessary model fitting and is computationally efficient
        drift = k_t.diff().mean()

        # Store last year and last k_t
        last_year = int(mtx.columns[-1])
        last_k_t = k_t.iloc[-1]

        # Assign fitted parameters back to self
        self.a_x = a_x
        self.b_x = b_x
        self.k_t = k_t
        self.drift = drift
        self.last_year = last_year
        self.last_k_t = last_k_t
        self.fitted = True

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict rates for a given feature DataFrame.

        The Lee-Carter model predicts log mortality rates as:
            log(m_x,t) = a_x + b_x * k_t
        where:
            - a_x captures the average age-specific mortality
            - b_x captures the sensitivity of mortality at age x to changes in k_t
            - k_t captures the overall level of mortality at time t

        Predictions for future years are made by extrapolating k_t using the estimated drift following:
            k_{T+n} = k_T + n * drift
        where
            - k_{T+n}: Predicted value of k_t for year T+n
            - k_T: Last observed value of k_t in the training data
            - drift: Estimated drift of the time index

        The extended k_t is then combined with the age-specific parameters a_x and b_x to produce
        predicted log mortality rates, which are subsequently exponentiated to obtain the
        predicted mortality rates.

        If a decay parameter phi is specified, the drift is adjusted by the decay factor for each step ahead:
            k_{T+n} = k_T + (drift * (phi + phi^2 + ... + phi^n))
        where
            - phi: Decay parameter adjusting the contribution of the drift for each step ahead

        A smaller phi reduces the impact of the drift for future years, effectively damping the
        extrapolation of k_t, while a phi close to 1 maintains most of the drift's impact for
        future years.

        Args:
            X (pd.DataFrame): Feature DataFrame with 'year' and 'age' columns

        Returns:
            np.ndarray: Predicted rates
        """
        # Check if model has been fitted
        if not self.fitted:
            raise ValueError("Model must be fitted before calling predict")

        required_cols = ["year", "age"]
        missing_cols = [col for col in required_cols if col not in X.columns]
        if missing_cols:
            raise ValueError(f"X must contain columns: {missing_cols}")

        preds = []
        for _, row in X.iterrows():
            age = int(row["age"])
            n_steps = int(row["year"]) - self.last_year
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


def generate_mortality_forecast(
    training_years: list[int],
    increments: list[int],
    phi: float | None = None,
    output_path: str | None = None,
) -> pd.DataFrame:
    """Generate mortality forecast using the Lee-Carter model.

    Calculates single-year-of-age mortality rates for each training year, then
    fits a separate Lee-Carter model to each sex and race/ethnicity group. Each
    model uses the historical mortality, optionally damped by `phi`, to
    forecast rates for every age in each of the requested increment years.

    Args:
        training_years (list[int]): List of years to use for training the model
        increments (list[int]): List of increment years to forecast
        phi (float | None): Optional decay parameter. Defaults to None.
        output_path (str | None): Path where the forecast CSV will be saved. If
            None, the forecast is not saved. Defaults to None.

    Returns:
        pd.DataFrame: Forecasted mortality rates
    """
    rates = pd.concat(
        [get_mortality_rates(year).assign(year=year) for year in training_years],
        ignore_index=True,
    )

    # Within each sex and ethnicity group, fit a separate Lee-Carter model
    # and forecast increment years
    forecasts = []
    for sex in rates["sex"].unique():
        for ethnicity in rates["ethnicity"].unique():
            model = LeeCarterModel(phi=phi)
            group = rates.loc[(rates["sex"] == sex) & (rates["ethnicity"] == ethnicity)]

            # Create training data and fit Lee-Carter model
            model.fit(X=group[["year", "age"]], y=group["rate_death"])

            # Create forecasts for specified increment years
            ages = group["age"].unique()
            for increment in increments:
                X_forecast = pd.DataFrame({"year": increment, "age": ages})
                result = X_forecast.assign(
                    sex=sex,
                    ethnicity=ethnicity,
                    rate_death=model.predict(X_forecast),
                )

                forecasts.append(result)

    df_forecast = pd.concat(forecasts, ignore_index=True)

    if output_path is not None:
        df_forecast.to_csv(output_path, index=False)

    return df_forecast
