param(
    [int]$Epochs = 250
)

python scripts/kivanc_futures_workflow.py risk-hyperopt-validate `
  --epochs $Epochs `
  --label kivanc_futures_1d_risk_hyperopt
