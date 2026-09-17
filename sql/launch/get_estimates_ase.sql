-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;


-- Get age/sex/ethnicity by population type from SANDAG's Estimates Program --
SELECT
    @year AS [year],
    [pop_type],
    [age_group],
    [sex],
    [ethnicity],
    [value]
FROM [EstimatesProgram].[inputs].[controls_ase]
WHERE
    [run_id] = @run_id
    AND [year] = @year
ORDER BY
    [pop_type],
    [age_group],
    [sex],
    [ethnicity]