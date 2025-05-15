SELECT
    [run_id]
    , [user]
    , [date]
    , [version]
    , [comments]
    , [launch]
    , [horizon]
FROM [metadata].[run]
WHERE [loaded] = 1