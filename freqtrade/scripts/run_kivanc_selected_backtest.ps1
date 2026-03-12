param(
    [string]$Scenario = "",
    [string]$Date = "",
    [switch]$PrintOnly
)

$selectorScript = Join-Path $PSScriptRoot "kivanc_runtime_selector.py"
$selectorArgs = @($selectorScript)
if ($Scenario) {
  $selectorArgs += @("--scenario", $Scenario)
}
if ($Date) {
  $selectorArgs += @("--date", $Date)
}

$selection = python @selectorArgs | ConvertFrom-Json

$output = [ordered]@{
  scenario = $selection.scenario
  selection_source = $selection.selection_source
  preferred_mode = $selection.preferred_mode
  timerange = $selection.timerange
  reason = $selection.reason
  comparison_report = $selection.comparison_report
}
$output | ConvertTo-Json -Depth 3

if ($PrintOnly -or $selection.preferred_mode -eq "none") {
  return
}

$freqtradeRoot = Split-Path $PSScriptRoot -Parent

if ($selection.preferred_mode -eq "spot_1d") {
  $scriptPath = Join-Path $PSScriptRoot "backtest_kivanc_1d.ps1"
  Push-Location $freqtradeRoot
  try {
    powershell -ExecutionPolicy Bypass -File $scriptPath -Timerange $selection.timerange
  }
  finally {
    Pop-Location
  }
  return
}

if ($selection.preferred_mode -eq "futures_1d") {
  $scriptPath = Join-Path $PSScriptRoot "backtest_kivanc_futures_1d.ps1"
  Push-Location $freqtradeRoot
  try {
    powershell -ExecutionPolicy Bypass -File $scriptPath -Timerange $selection.timerange
  }
  finally {
    Pop-Location
  }
  return
}

if ($selection.preferred_mode -eq "filtered_futures_1d") {
  $scriptPath = Join-Path $PSScriptRoot "backtest_kivanc_futures_filtered_1d.ps1"
  Push-Location $freqtradeRoot
  try {
    powershell -ExecutionPolicy Bypass -File $scriptPath -Timerange $selection.timerange
  }
  finally {
    Pop-Location
  }
  return
}

throw "Unsupported preferred_mode: $($selection.preferred_mode)"
