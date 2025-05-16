SELECT 
      [year],
      [race],
      [sex],
      [age],
      [pop],
      [pop_mil],
      [gq],
      [hh],
      [hh_head_lf],
      [child1],
      [senior1],
      [size1],
      [size2],
      [size3],
      [workers0],
      [workers1],
      [workers2],
      [workers3],
      [run_id]
FROM [outputs].[population]
WHERE [run_id] = {run_id}
