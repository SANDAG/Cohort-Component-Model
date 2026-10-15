/*
Get the Group Quarters Formation Rates from SANDAG's Estimates Program.
Rates by age group, sex, and race/ethnicity are calculated directly from
the Estimates Program output with no additional adjustments needed.

Only the "Group Quarters - Other" type has rates calculated directly from
the Estimates Program output as the Cohort Component Model holds
"Group Quarters - College", "Group Quarters - Military", and
"Group Quarters - Institutional Correctional Facilities" types constant.

Note this script must be run in the production Estimates Program database.
*/

DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;

SELECT
    [age_group],
    [sex],
    [ethnicity],
    1.0 * SUM(CASE WHEN [pop_type] = 'Group Quarters - Other' THEN [value] ELSE 0 END) / SUM([value]) AS [rate_gq_other]
FROM [inputs].[controls_ase]
WHERE
    [run_id] = @run_id
    AND [year] = @year
    -- Remove College, Military, and Institutional Correctional Facilities types
    AND [pop_type] NOT IN (
        'Group Quarters - College',
        'Group Quarters - Military',
        'Group Quarters - Institutional Correctional Facilities'
    )
GROUP BY
    [age_group],
    [sex],
    [ethnicity]
ORDER BY
    [age_group],
    [sex],
    [ethnicity]