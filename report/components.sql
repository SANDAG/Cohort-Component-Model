SELECT 
      [year],
      [race],
      [sex],
      [age],
      [deaths],
      [births],
      [ins],
      [outs],
      [run_id]
FROM [outputs].[components]
WHERE [run_id] = {run_id}
