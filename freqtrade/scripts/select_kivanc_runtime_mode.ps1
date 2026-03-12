param(
    [string]$Scenario = "",
    [string]$Date = ""
)

$scriptPath = Join-Path $PSScriptRoot "kivanc_runtime_selector.py"
$argsList = @($scriptPath)
if ($Scenario) {
  $argsList += @("--scenario", $Scenario)
}
if ($Date) {
  $argsList += @("--date", $Date)
}

python @argsList
