SELECT 
      [year],
      [race],
      [sex],
      [age],
      [rate_birth],
      [rate_death],
      [rate_in],
      [rate_out],
      [rate_gq],
      [rate_hh],
      [rate_hh_head_lf],
      [rate_size1],
      [rate_size2],
      [rate_size3],
      [rate_child1],
      [rate_senior1],
      [rate_workers0],
      [rate_workers1],
      [rate_workers2],
      [rate_workers3],
      [run_id]
FROM [outputs].[rates]
WHERE [run_id] = {run_id}
