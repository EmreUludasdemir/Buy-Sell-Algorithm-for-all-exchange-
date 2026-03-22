param(
    [string]$Scenario = "",
    [string]$Date = "",
    [string]$ContainerName = "kivanc_auto_runtime",
    [string]$FallbackMode = "spot_1d",
    [int]$ApiHostPort = 0,
    [switch]$ExposeApi,
    [switch]$PrintOnly,
    [switch]$Strict
)

$starterScript = Join-Path $PSScriptRoot "start_kivanc_selected_runtime.ps1"
$starterArgs = @{
  ContainerName = $ContainerName
}

if ($Scenario) {
  $starterArgs["Scenario"] = $Scenario
}
if ($Date) {
  $starterArgs["Date"] = $Date
}
if ($ExposeApi) {
  $starterArgs["ExposeApi"] = $true
}
if ($ApiHostPort -gt 0) {
  $starterArgs["ApiHostPort"] = $ApiHostPort
}
if ($PrintOnly) {
  $starterArgs["PrintOnly"] = $true
}
if (-not $Strict) {
  $starterArgs["FallbackMode"] = $FallbackMode
}

& $starterScript @starterArgs
