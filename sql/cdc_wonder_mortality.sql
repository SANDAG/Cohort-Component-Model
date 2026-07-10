-- Get CDC WONDER mortality data

SELECT [product]
      ,[location]
      ,[period]
      ,[year]
      ,[age]
      ,[sex]
      ,[hispanic_origin]
      ,[race]
      ,[deaths]
      ,[pop]
  FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
  ORDER BY [year], [race], [sex], [age]