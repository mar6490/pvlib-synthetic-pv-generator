# Pipeline

## Input

Weather CSV (5-min resolution) Meta JSON

## Processing Steps

1.  Parse timestamps → fixed UTC+01:00
2.  Validate time regularity
3.  Generate system scenarios
4.  Compute solar position
5.  Calculate DNI
6.  Calculate POA
7.  Compute DC
8.  Compute AC
9.  Export CSV
10. Optional quicklook

## Output

-   system_XXX.csv
-   systems_metadata.csv
