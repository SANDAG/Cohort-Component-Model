-- Get the total State of California active-duty military population
with
    [pums_persons]
    AS
    (
                    SELECT 2020 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2016_2020_persons]
        UNION ALL
            SELECT 2021 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2017_2021_persons]
    )
SELECT
    [year], SUM([PWGTP]) AS [pop_ca_mil]
FROM
    [pums_persons]
WHERE [ST] = '06' AND MIL = '1'
GROUP BY [year];