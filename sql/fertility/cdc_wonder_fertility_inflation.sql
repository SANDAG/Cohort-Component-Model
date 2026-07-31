/* 
    This query calculates the CDC WONDER fertility inflation factors that will be used to
    inflate births. The inflation factor is calculated as 1 + (Not Stated Births / 
    Total Births) for each year and location. 
*/

DECLARE @year INTEGER = :year;

BEGIN
    -- Add check with THROW statement if the year provided does not exist in the dataset
    IF NOT EXISTS (SELECT 1 FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility] WHERE [year] = @year)
        THROW 50002, 'The provided year does not exist in the CDC WONDER fertility dataset', 1
END;

SELECT
    [year],
    [location],
    1 + SUM(
        CASE
            WHEN [race] = 'Not Stated' OR [hispanic_origin] = 'Not Stated' THEN [births]
            ELSE 0
        END) / SUM([births]) * 1.0 AS [inflation_factor]
FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility]
WHERE
    -- We load "Hispanic or Latino; Not Hispanic or Latino" to combine with "Not Stated" Race
    -- And "Not Stated" Hispanic Origin to combine with "All Races" to account for "Not Stated" Records
    -- We load "Hispanic or Latino" and "Not Hispanic or Latino"
    -- To make the calculation of total births 
    [hispanic_origin] IN ('Hispanic or Latino', 'Not Hispanic or Latino', 'Not Stated', 'Hispanic or Latino; Not Hispanic or Latino')
    AND [race] IN ('All Races', 'Not Stated') AND [age] NOT IN ('Under 15 years', '50 years and over')
    AND [year] = @year
GROUP BY
    [year],
    [location]
ORDER BY
    [year],
    [location]