-- Get the total State of California active-duty military population
-- TODO: Migrate to [acs] database and add 2006-2010 up to 2016-2021 PUMS files
with
    [pums_persons]
    AS
    (
                    SELECT 2020 AS [year], [ST], [MIL], [PWGTP]
            FROM [census].[acs_pums].[y2020_p_us_a]
        UNION ALL
            SELECT 2020 AS [year], [ST], [MIL], [PWGTP]
            FROM [census].[acs_pums].[y2020_p_us_b]
    )
SELECT
    [year], SUM([PWGTP]) AS [pop_ca_mil]
FROM
    [pums_persons]
WHERE [ST] = '06' AND MIL = '1'
GROUP BY [year]