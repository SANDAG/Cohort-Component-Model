/*
Get household and housing unit information from SANDAG's Estimates Program.

Total housing stock and households by structure type are returned along with
the proportions of non-Mobile Home households by structure type and vacancy
rates by structure type (excluding Mobile Homes).

Note this script must be run in the production Estimates Program database.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year integer = :year;

WITH [housing] AS (
    SELECT
        CASE
            WHEN [hs].[structure_type] IN ('Single Family - Detached', 'Single Family - Multiple Unit') THEN 'Single Family'
            ELSE [hs].[structure_type]
        END AS [structure_type],
        [hs].[value] AS [hs],
        [hh].[value] AS [hh]
    FROM [outputs].[hs]
    INNER JOIN [outputs].[hh]
        ON [hs].[run_id] = [hh].[run_id]
        AND [hs].[year] = [hh].[year]
        AND [hs].[mgra] = [hh].[mgra]
        AND [hs].[structure_type] = [hh].[structure_type]
    WHERE [hs].[run_id] = @run_id
        AND [hs].[year] = @year
),
[totals] AS (
    SELECT
        [structure_type],
        SUM([hs]) AS [hs],
        SUM([hh]) AS [hh]
    FROM [housing]
    GROUP BY [structure_type]
)
SELECT
    [structure_type],
    [hs],
    [hh],
    CASE
        WHEN [structure_type] = 'Mobile Home' THEN NULL
        ELSE 1.0 * [hh] / (SELECT SUM([hh]) FROM [totals] WHERE [structure_type] != 'Mobile Home')
    END AS [hh_pct],
    CASE
        WHEN [structure_type] = 'Mobile Home' THEN NULL
        ELSE 1.0 * ([hs]-[hh]) / [hs]
    END AS [vacancy_rate]
FROM [totals]
ORDER BY [structure_type]