param(
    [string]$Timerange = "20220101-20260301",
    [int]$MinPairs = 3,
    [int]$Top = 10
)

$scriptPath = Join-Path $PSScriptRoot "kivanc_futures_pairset_scan.py"

python $scriptPath `
  --timerange $Timerange `
  --min-pairs $MinPairs `
  --top $Top
