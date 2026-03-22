param(
    [int]$Epochs = 250
)

$scriptPath = Join-Path $PSScriptRoot "kivanc_futures_workflow.py"

python $scriptPath risk-hyperopt-validate `
  --variant filtered_futures `
  --epochs $Epochs `
  --label kivanc_futures_filtered_1d_risk_hyperopt
