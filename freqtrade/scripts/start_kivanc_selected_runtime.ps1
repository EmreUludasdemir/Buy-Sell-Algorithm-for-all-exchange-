param(
    [string]$Scenario = "",
    [string]$Date = "",
    [string]$ContainerName = "kivanc_selected_runtime",
    [string]$OverrideMode = "",
    [string]$FallbackMode = "",
    [int]$ApiHostPort = 0,
    [switch]$ExposeApi,
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

$modeMap = @{
  "spot_1d" = @{
    Config = "config.json"
    Strategy = "KivancSupertrendedMovingAverages1D"
    StrategyPath = ""
    LogStem = "kivanc_stma_runtime_spot"
    DbStem = "tradesv3_kivanc_runtime_spot"
    ApiContainerPort = 8080
    DefaultApiHostPort = 8090
  }
  "futures_1d" = @{
    Config = "config_futures_research.json"
    Strategy = "KivancSupertrendedMovingAveragesFutures1D"
    StrategyPath = "user_data/strategies_research"
    LogStem = "kivanc_stma_runtime_futures"
    DbStem = "tradesv3_kivanc_runtime_futures"
    ApiContainerPort = 8081
    DefaultApiHostPort = 8091
  }
  "filtered_futures_1d" = @{
    Config = "config_futures_filtered_research.json"
    Strategy = "KivancSupertrendedMovingAveragesFutures1D"
    StrategyPath = "user_data/strategies_research"
    LogStem = "kivanc_stma_runtime_filtered_futures"
    DbStem = "tradesv3_kivanc_runtime_filtered_futures"
    ApiContainerPort = 8082
    DefaultApiHostPort = 8092
  }
}

$preferredMode = $selection.preferred_mode
$effectiveMode = $preferredMode
$modeSource = "selector"
if ($OverrideMode) {
  $effectiveMode = $OverrideMode
  $modeSource = "override"
}
elseif ($preferredMode -eq "none" -and $FallbackMode) {
  $effectiveMode = $FallbackMode
  $modeSource = "fallback"
}

$output = [ordered]@{
  scenario = $selection.scenario
  selection_source = $selection.selection_source
  preferred_mode = $preferredMode
  effective_mode = $effectiveMode
  mode_source = $modeSource
  timerange = $selection.timerange
  reason = $selection.reason
  comparison_report = $selection.comparison_report
  container_name = $ContainerName
}

if ($PrintOnly -or $effectiveMode -eq "none") {
  $output | ConvertTo-Json -Depth 3
  return
}

if (-not $modeMap.ContainsKey($effectiveMode)) {
  throw "Unsupported runtime mode: $effectiveMode"
}

$mode = $modeMap[$effectiveMode]
$runtimeConfig = $mode.Config
$resolvedApiHostPort = $null
$runtimeConfigForOutput = $runtimeConfig
$containerSlug = ($ContainerName -replace '[^A-Za-z0-9_.-]', '_')
$logFile = "$($mode.LogStem).$containerSlug.log"
$dbFile = "$($mode.DbStem).$containerSlug.sqlite"
$existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
if ($existing) {
  docker rm -f $ContainerName | Out-Null
}

$freqtradeRoot = Split-Path $PSScriptRoot -Parent
Push-Location $freqtradeRoot
try {
  $dockerArgs = @("compose", "run", "-d", "--name", $ContainerName)
  if ($ExposeApi) {
    $resolvedApiHostPort = $ApiHostPort
    if ($resolvedApiHostPort -le 0) {
      $resolvedApiHostPort = $mode.DefaultApiHostPort
    }

    $runtimeConfigDir = Join-Path $freqtradeRoot "user_data\\runtime_configs"
    New-Item -ItemType Directory -Force -Path $runtimeConfigDir | Out-Null
    $runtimeConfigFile = "$ContainerName.$effectiveMode.json"
    $runtimeConfigPath = Join-Path $runtimeConfigDir $runtimeConfigFile

    $baseConfigPath = Join-Path $freqtradeRoot "user_data\\$($mode.Config)"
    $runtimePayload = Get-Content -Raw -Path $baseConfigPath | ConvertFrom-Json
    if (-not $runtimePayload.api_server) {
      $runtimePayload | Add-Member -NotePropertyName api_server -NotePropertyValue ([pscustomobject]@{})
    }
    $runtimePayload.api_server.enabled = $true
    $runtimePayload.api_server.listen_ip_address = "0.0.0.0"
    $runtimePayload.api_server.listen_port = $mode.ApiContainerPort
    $runtimePayload.api_server.verbosity = "error"
    $runtimePayload.api_server.enable_openapi = $true
    $runtimePayload.api_server.jwt_secret_key = "change-me"
    $runtimePayload.api_server.ws_token = "change-me"
    $runtimePayload.api_server.username = "freqtrade"
    $runtimePayload.api_server.password = "change-me"
    $runtimePayload.bot_name = "$($runtimePayload.bot_name)_runtime"
    $runtimeJson = $runtimePayload | ConvertTo-Json -Depth 100
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($runtimeConfigPath, $runtimeJson, $utf8NoBom)

    $runtimeConfig = "runtime_configs/$runtimeConfigFile"
    $runtimeConfigForOutput = $runtimeConfig
    $dockerArgs += @("--publish", "$resolvedApiHostPort`:$($mode.ApiContainerPort)")
  }

  $output["api_host_port"] = $resolvedApiHostPort
  $output["api_container_port"] = $(if ($ExposeApi) { $mode.ApiContainerPort } else { $null })
  $output["runtime_config"] = $runtimeConfigForOutput
  $output | ConvertTo-Json -Depth 3

  $dockerArgs += @(
    "bot1_btceth",
    "trade",
    "--logfile", "/freqtrade/user_data/$logFile",
    "--db-url", "sqlite:////freqtrade/user_data/$dbFile",
    "--config", "/freqtrade/user_data/$runtimeConfig",
    "--strategy", $mode.Strategy
  )
  if ($mode.StrategyPath) {
    $dockerArgs += @("--strategy-path", $mode.StrategyPath)
  }

  $containerId = docker @dockerArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to start selected runtime container."
  }
  $containerId.Trim()
}
finally {
  Pop-Location
}
