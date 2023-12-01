-- Create temporary table of Census 2010 San Diego County PUMAs
DROP TABLE IF EXISTS tt_sd_pumas_2010
DECLARE @tt_sd_pumas_2010 TABLE ([PUMA] varchar(5))
INSERT INTO @tt_sd_pumas_2010
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

-- Get San Diego County single year of age, race, sex population from ACS PUMS.
-- TODO: Migrate to [acs] database and add 2006-2010 up to 2016-2021 PUMS files
with
	[pums_persons]
	AS
	(
					SELECT 2020 AS [year], [ST], [PUMA], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], [SPORDER], [PWGTP]
			FROM [census].[acs_pums].[y2020_p_us_a]
		UNION ALL
			SELECT 2020 AS [year], [ST], [PUMA], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], [SPORDER], [PWGTP]
			FROM [census].[acs_pums].[y2020_p_us_b]
	),
	[transformed_tt]
	AS
	(
		SELECT
			[year],
			CASE WHEN [AGEP] > 110 THEN 110 ELSE [AGEP] END AS [age],
			CASE WHEN [SEX] = '1' THEN 'M' WHEN [SEX] = '2' THEN 'F' ELSE NULL END AS [sex],
			CASE	WHEN [HISP] != '01' THEN 'Hispanic'  -- Hispanic takes precendence over Race
				WHEN [RAC1P] IN ('1','8') THEN 'White alone'  -- both White and Other
				WHEN [RAC1P] = '2' THEN 'Black or African American alone'
				WHEN [RAC1P] IN ('3','4','5') THEN 'American Indian or Alaska Native alone'
				WHEN [RAC1P] = '6' THEN 'Asian alone'
				WHEN [RAC1P] = '7' THEN 'Native Hawaiian and Other Pacific Islander alone'
				WHEN [RAC1P] = '9' THEN 'Two or More Races'
				ELSE NULL END AS [race],
			[MIL],
			[RELSHIPP],
			[SPORDER],
			[PWGTP]
		FROM
			[pums_persons]
		WHERE  -- Note the [ST] and [PUMA] fields are specific to certain years of ACS
		([year] = 2020 AND [ST] = '06' -- 2016-2020 ACS uses 2010 Census PUMAS
			AND [PUMA] IN (SELECT [PUMA]
			FROM @tt_sd_pumas_2010))
	)
SELECT
	[year],
	[race],
	[sex],
	[age],
	SUM([PWGTP]) AS [pop],
	SUM(CASE WHEN [MIL] = '1' THEN [PWGTP] ELSE 0 END) AS [pop_mil],
	SUM(CASE WHEN [RELSHIPP] IN ('37','38') THEN [PWGTP] ELSE 0 END) AS [pop_gq],
	SUM(CASE WHEN [RELSHIPP] NOT IN ('37','38') THEN [PWGTP] ELSE 0 END) AS [pop_hh],
	SUM(CASE WHEN [RELSHIPP] NOT IN ('37','38') AND [SPORDER] = 1 THEN [PWGTP] ELSE 0 END) AS [pop_hh_head]
FROM
	[transformed_tt]
GROUP BY
	[year],
	[race],
	[sex],
	[age]