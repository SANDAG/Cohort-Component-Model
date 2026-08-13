/* 
    This query calculates the CDC WONDER fertility inflation factors that will be used to
    inflate births. The inflation factor is calculated as 1 + (Not Stated Births / 
    Total Births) for each year and location. 
*/

DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(49) = 'Data for CDC WONDER fertility year does not exist';
DECLARE @product NVARCHAR(9) = CASE
    WHEN @year >= 2020 THEN '2020+'
    WHEN @year <= 2019 THEN '2007-2019'
    ELSE NULL END;

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility]
    WHERE 
        [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN

    SELECT
        [year],
        [location],
        1 + SUM(
            CASE
                WHEN [race] = 'Not Stated' OR [hispanic_origin] = 'Not Stated' OR [age] IN ('Under 15 years' ,'45-49 years', '50 years and over') THEN [births]
                ELSE 0
            END) / SUM([births]) * 1.0 AS [inflation_factor]
    FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility]
    WHERE
        -- We load "Hispanic or Latino; Not Hispanic or Latino" to combine with "Not Stated" Race
        -- And "Not Stated" Hispanic Origin to combine with "All Races" to account for "Not Stated" Records
        -- We load "Hispanic or Latino" and "Not Hispanic or Latino"
        -- To make the calculation of total births 
        [hispanic_origin] IN ('Hispanic or Latino', 'Not Hispanic or Latino', 'Not Stated', 'Hispanic or Latino; Not Hispanic or Latino')
        AND [race] IN ('All Races', 'Not Stated')
        AND [year] = @year
    GROUP BY
        [year],
        [location]
    ORDER BY
        [year],
        [location]
END;