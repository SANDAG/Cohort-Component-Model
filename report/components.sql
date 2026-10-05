SELECT 
      [run_id]
      ,[year]
      ,[age]
      ,[sex]
      ,[ethnicity]
      ,[births]
      ,[deaths]
      ,[ins]
      ,[outs]
FROM [outputs].[components]
WHERE [run_id] = {run_id}