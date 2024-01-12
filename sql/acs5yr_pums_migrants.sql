-- Create temporary table of Census 2010 San Diego County PUMAs
-- 5yr ACS PUMS from 2012-2016 to 2017-2021 use 2010 Census PUMAS
DROP TABLE IF EXISTS tt_sd_pumas_2010
DECLARE @tt_sd_pumas_2010 TABLE ([PUMA] varchar(5))
INSERT INTO
    @tt_sd_pumas_2010
    ([PUMA])
VALUES
    ('07301'),
    ('07302'),
    ('07303'),
    ('07304'),
    ('07305'),
    ('07306'),
    ('07307'),
    ('07308'),
    ('07309'),
    ('07310'),
    ('07311'),
    ('07312'),
    ('07313'),
    ('07314'),
    ('07315'),
    ('07316'),
    ('07317'),
    ('07318'),
    ('07319'),
    ('07320'),
    ('07321'),
    ('07322');

-- Get single year of age, race, sex in/out migration for San Diego County from ACS PUMS.
with
    [pums_persons]
    AS
    (
                    SELECT
                2020 AS [year],
                [ST],
                [PUMA],
                [AGEP],
                [SEX],
                [HISP],
                [RAC1P],
                [MIL],
                [MIG],
                [MIGSP],
                [MIGPUMA],
                [PWGTP]
            FROM
                [acs].[pums].[5y_2016_2020_persons]
        UNION
    ALL
            SELECT
                2021 AS [year],
                [ST],
                [PUMA],
                [AGEP],
                [SEX],
                [HISP],
                [RAC1P],
                [MIL],
                [MIG],
                [MIGSP],
                [MIGPUMA],
                [PWGTP]
            FROM
                [acs].[pums].[5y_2017_2021_persons]
    ),
    [transformed_tt]
    AS
    (
        SELECT
            [year],
            CASE
            WHEN [AGEP] > 110 THEN 110
            ELSE [AGEP]
        END AS [age],
            CASE
            WHEN [SEX] = '1' THEN 'M'
            WHEN [SEX] = '2' THEN 'F'
            ELSE NULL
        END AS [sex],
            CASE
            WHEN [HISP] != '01' THEN 'Hispanic' -- Hispanic takes precendence over Race
            WHEN [RAC1P] IN ('1', '8') THEN 'White alone' -- both White and Other
            WHEN [RAC1P] = '2' THEN 'Black or African American alone'
            WHEN [RAC1P] IN ('3', '4', '5') THEN 'American Indian or Alaska Native alone'
            WHEN [RAC1P] = '6' THEN 'Asian alone'
            WHEN [RAC1P] = '7' THEN 'Native Hawaiian or Other Pacific Islander alone'
            WHEN [RAC1P] = '9' THEN 'Two or More Races'
            ELSE NULL
        END AS [race],
            CASE
            WHEN [year] BETWEEN 2016
            AND 2021
                AND (
                [MIGSP] != '006'
                OR (
                    [MIGSP] = '006'
                AND [MIGPUMA] != '07300'
                )
            ) -- 2010 Census Migration PUMA for San Diego County
                AND [ST] = '06'
                AND [PUMA] IN (
                SELECT
                    [PUMA]
                FROM
                    @tt_sd_pumas_2010
            ) -- 2016-2020 ACS uses 2010 Census PUMAS
            THEN [PWGTP]
            ELSE 0
        END AS [in],
            CASE
            WHEN [year] BETWEEN 2016
            AND 2021
                AND (
                [MIGSP] = '006'
                AND [MIGPUMA] = '07300'
            ) -- 2010 Census Migration PUMA for San Diego County
                AND (
                [ST] != '06'
                OR (
                    [ST] = '06'
                AND [PUMA] NOT IN (
                        SELECT
                    [PUMA]
                FROM
                    @tt_sd_pumas_2010
                    )
                )
            ) THEN [PWGTP]
            ELSE 0
        END AS [out]
        FROM
            [pums_persons]
        WHERE
        [MIL] != '1' -- remove active-duty military
            AND [MIG] IN ('2', '3')
        -- foreign/domestic migrants
    )
SELECT
    [year],
    [race],
    [sex],
    [age],
    SUM([in]) AS [in],
    SUM([out]) AS [out]
FROM
    [transformed_tt]
GROUP BY
    [year],
    [race],
    [sex],
    [age];