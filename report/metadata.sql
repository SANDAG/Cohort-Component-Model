SELECT 
    [run_id]
    ,[launch]
    ,[horizon]
    ,[user]
    ,[start_date]
    ,[end_date]
    ,[version]
    ,[comments]
    ,[complete]
FROM [metadata].[run]
WHERE [complete] = 1