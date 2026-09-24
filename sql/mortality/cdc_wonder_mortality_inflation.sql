/* 
    This query calculates the CDC WONDER mortality inflation factors to account
    for deaths attributed to unknown demographic groups.
    
    Some records in the CDC WONDER mortality dataset contain incomplete
    demographic information. These deaths occurred but cannot be  assigned to
    specific demographic groups. By inflating the counts for known groups, we
    proportionally distribute these unassigned deaths.
    
    The inflation factor is calculated as 1 + (Unknown Deaths / Total Deaths)
    for each year  and location.

    Unknown deaths are defined as deaths that are:
        1) assigned to "Not Stated" age
        2) assigned to "Not Stated" hispanic origin
*/

DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(49) = 'Data for CDC WONDER mortality year does not exist';
DECLARE @product NVARCHAR(9) = CASE
    WHEN @year >= 2021 THEN '2018+'
    WHEN @year <=2020 THEN '1999-2020'
    ELSE NULL END;

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
    WHERE 
        [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN
    SELECT
        [location],
        [sex],
        1 + SUM(
            CASE
                WHEN [age] = 'Not Stated' OR [hispanic_origin] = 'Not Stated' THEN [deaths]
                ELSE 0
            END) 
            / 
            SUM(
            CASE
                WHEN [age] = 'All Stated Ages' AND [race] = 'All Races' THEN [deaths]
                ELSE 0
            END) * 1.0 AS [inflation_factor]
    FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
    WHERE
        [product] = @product
        -- Five year rolling sums used
        AND [period] = 'Five-Year'
        AND [year] = @year
    GROUP BY
        [location],
        [sex]
    ORDER BY
        [location],
        [sex]
END;