/*
Get totals for household characteristics for San Diego County from SANDAG's Estimates Program.

Note this script must be run in the production Estimates Program database.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year integer = :year;

SELECT
	SUM(CASE WHEN [metric] = 'Household Size - 1' THEN [value] ELSE 0 END) AS [hh_size1],
	SUM(CASE WHEN [metric] = 'Household Size - 2' THEN [value] ELSE 0 END) AS [hh_size2],
	SUM(CASE WHEN [metric] = 'Household Size - 3' THEN [value] ELSE 0 END) AS [hh_size3],
	SUM(CASE WHEN [metric] = 'Household Size - 4' THEN [value] ELSE 0 END) AS [hh_size4],
	SUM(CASE WHEN [metric] = 'Household Size - 5' THEN [value] ELSE 0 END) AS [hh_size5],
	SUM(CASE WHEN [metric] = 'Household Size - 6' THEN [value] ELSE 0 END) AS [hh_size6],
	SUM(CASE WHEN [metric] = 'Household Size - 7+' THEN [value] ELSE 0 END) AS [hh_size7],
	SUM(CASE WHEN [metric] = 'Household Workers - 0' THEN [value] ELSE 0 END) AS [hh_workers0],
	SUM(CASE WHEN [metric] = 'Household Workers - 1' THEN [value] ELSE 0 END) AS [hh_workers1],
	SUM(CASE WHEN [metric] = 'Household Workers - 2' THEN [value] ELSE 0 END) AS [hh_workers2],
	SUM(CASE WHEN [metric] = 'Household Workers - 3+' THEN [value] ELSE 0 END) AS [hh_workers3]
FROM [outputs].[hh_characteristics]
WHERE [run_id] = @run_id
  AND [year] = @year;