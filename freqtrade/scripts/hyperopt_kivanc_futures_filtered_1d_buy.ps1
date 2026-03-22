param(
    [int]$Epochs = 250
)

$scriptPath = Join-Path $PSScriptRoot "kivanc_futures_workflow.py"

python $scriptPath buy-hyperopt-validate `
  --variant filtered_futures `
  --epochs $Epochs `
  --label kivanc_futures_filtered_1d_buy_hyperopt
