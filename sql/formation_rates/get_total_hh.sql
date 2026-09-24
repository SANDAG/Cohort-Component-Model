/*
Get total households for San Diego County from SANDAG's Estimates Program.

Note this script must be run in the production Estimates Program database.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year integer = :year;

SELECT SUM([value]) AS [hh]
FROM [outputs].[hh]
WHERE [run_id] = @run_id
  AND [year] = @year;