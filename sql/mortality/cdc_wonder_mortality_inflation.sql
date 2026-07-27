/* This query calculates the CDC WONDER mortality inflation factors that will be used to
inflate deaths. The inflation factor is calculated as 1 + (Not Stated Deaths / 
Total Deaths) for each year, location, and sex. 
*/

DECLARE @year INTEGER = :year;

-- 2021 data is unavailable, fall back to 2020
IF @year = 2021 AND NOT EXISTS (
    SELECT 1 FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality] 
    WHERE [year] = 2021
)
BEGIN
	  SET @year = 2020;
END
ELSE
BEGIN
    -- For all other years, throw error if year doesn't exist
    IF NOT EXISTS (
      SELECT 1 FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality] 
      WHERE [year] = @year
    )
    THROW 50002, 'The provided year does not exist in the CDC WONDER mortality dataset', 1;
END;

SELECT
    [year],
    [location],
    CASE [sex]
        WHEN 'Female' THEN 'F'
        WHEN 'Male' THEN 'M'
    END AS [sex],
    1 + SUM(
        CASE
            WHEN [age] = 'Not Stated' OR [hispanic_origin] = 'Not Stated' THEN [deaths]
            ELSE 0
        END) / SUM(
        CASE 
            WHEN [year] >= 2022 AND [location] = 'San Diego County' THEN [deaths] / 5.0
            ELSE [deaths]
        END) * 1.0 AS [inflation_factor]
FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
WHERE
    -- We load "All Stated Ages" specifically to capture "Not Stated" records in Hispanic Origin
    -- As we do not want to load in single year of age data for "Not Stated" Hispanic Origin records
    [age] IN ('All Stated Ages', 'Not Stated')
    -- We load "Hispanic or Latino; Not Hispanic or Latino" to combine with "All Stated Ages"
    -- To make the calculation of total deaths for stated categories easier
    -- We load "All Origins" to combine with "Not Stated" age
    AND [hispanic_origin] IN ('Hispanic or Latino; Not Hispanic or Latino', 'All Origins', 'Not Stated')
    AND [race] = 'All Races'
    AND [year] = @year
GROUP BY
    [year],
    [location],
    [sex]
ORDER BY
    [year],
    [location],
    [sex]