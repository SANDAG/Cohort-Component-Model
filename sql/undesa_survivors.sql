-- Get UN DESA mortality data
-- Filter to the most recent undesa_id to avoid duplicates

SELECT [undesa_id]
      ,[year]
      ,[age]
      ,[sex]
      ,[survivors]
  FROM [socioec_data].[vital_statistics].[undesa_survivors]
  WHERE [undesa_id] = (SELECT MAX([undesa_id]) FROM [socioec_data].[vital_statistics].[undesa_survivors])

