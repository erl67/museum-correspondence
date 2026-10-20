# Synthetic saved-response fixtures

These files are deliberately invented software test data. They are not transcriptions of
the museum scans, verified historical references, or evidence of model reading accuracy.
`truncated-response.json` retains a partial answer with an explicit token cutoff, for offline
replay of completion handling. Complete synthetic objects are constructed in `test/helpers.py`
and are also saved/recovered through the production journal/blob path in execution tests.
