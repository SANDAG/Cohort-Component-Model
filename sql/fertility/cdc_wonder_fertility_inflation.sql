/* 
    This query calculates the CDC WONDER fertility inflation factors that will be used to
    inflate birth rates for known demographic groups.
    
    Some records from the CDC WONDER natality dataset contain incomplete demographic information 
    (race/hispanic origin marked as "Not Stated") or fall outside the reproductive age range
    used in the model (under 15 or 45+). These births still occurred but cannot be assigned 
    to specific demographic groups. By inflating the rates for known groups, we proportionally
    distribute these unknown births so that the total modeled births matches the actual total
    births reported.
    
    The inflation factor is calculated as 1 + (Unknown Births / Total Births) for each year 
    and location.
    
    Unknown births are defined as births that are:
        1) assigned to age groups under 15 or over 44
        2) assigned to "Not Stated" race
        3) assigned to "Not Stated" hispanic origin
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
        1 + 1.0 * SUM(
            CASE
                WHEN (
                    [age] IN ('Under 15 years' ,'45-49 years', '50 years and over')
                    AND [race] = 'All Races'
                    AND [hispanic_origin] = 'All Origins'
                )              
                OR [race] = 'Not Stated' OR [hispanic_origin] = 'Not Stated'  
                THEN [births]
                ELSE 0
            END) / SUM([births]) AS [inflation_factor]
    FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility]
    WHERE
        [product] = @product
        -- Five year rolling sums used
        AND [period] = 'Five-Year'
        AND [year] = @year
        AND [births] > 0
    GROUP BY
        [year],
        [location]
    ORDER BY
        [year],
        [location]
END;