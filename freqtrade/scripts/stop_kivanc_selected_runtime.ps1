param(
    [string]$ContainerName = "kivanc_selected_runtime",
    [string]$Mode = "",
    [switch]$PurgeArtifacts,
    [switch]$PrintOnly
)

$artifactMap = @{
  "spot_1d" = @{
    LogStem = "kivanc_stma_runtime_spot"
    DbStem = "tradesv3_kivanc_runtime_spot"
  }
  "futures_1d" = @{
    LogStem = "kivanc_stma_runtime_futures"
    DbStem = "tradesv3_kivanc_runtime_futures"
  }
  "filtered_futures_1d" = @{
    LogStem = "kivanc_stma_runtime_filtered_futures"
    DbStem = "tradesv3_kivanc_runtime_filtered_futures"
  }
}

$freqtradeRoot = Split-Path $PSScriptRoot -Parent
$userDataRoot = Join-Path $freqtradeRoot "user_data"
$runtimeConfigDir = Join-Path $userDataRoot "runtime_configs"

$matchingConfigFiles = @()
if (Test-Path $runtimeConfigDir) {
  $configPattern = if ($Mode) { "$ContainerName.$Mode.json" } else { "$ContainerName.*.json" }
  $matchingConfigFiles = @(Get-ChildItem -Path $runtimeConfigDir -Filter $configPattern -File -ErrorAction SilentlyContinue)
}

$resolvedModes = @()
if ($Mode) {
  $resolvedModes = @($Mode)
}
elseif ($matchingConfigFiles.Count -gt 0) {
  $resolvedModes = @(
    $matchingConfigFiles |
      ForEach-Object {
        if ($_.BaseName -match "^[^.]+\.(.+)$") {
          $Matches[1]
        }
      } |
      Sort-Object -Unique
  )
}

if ($PurgeArtifacts -and $resolvedModes.Count -eq 0) {
  throw "Mode is required for -PurgeArtifacts when no runtime config can be used to infer it."
}

$artifactPaths = @()
$containerSlug = ($ContainerName -replace '[^A-Za-z0-9_.-]', '_')
foreach ($resolvedMode in $resolvedModes) {
  if (-not $artifactMap.ContainsKey($resolvedMode)) {
    throw "Unsupported runtime mode: $resolvedMode"
  }
  $artifactNames = @(
    "$($artifactMap[$resolvedMode].LogStem).$containerSlug.log",
    "$($artifactMap[$resolvedMode].DbStem).$containerSlug.sqlite",
    "$($artifactMap[$resolvedMode].DbStem).$containerSlug.sqlite-shm",
    "$($artifactMap[$resolvedMode].DbStem).$containerSlug.sqlite-wal"
  )
  foreach ($artifactName in $artifactNames) {
    $candidatePath = Join-Path $userDataRoot $artifactName
    if (Test-Path $candidatePath) {
      $artifactPaths += $candidatePath
    }
  }
}

$containerExists = [bool](docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName })
$output = [ordered]@{
  container_name = $ContainerName
  container_exists = $containerExists
  removed_container = $false
  resolved_modes = $resolvedModes
  removed_runtime_configs = @($matchingConfigFiles | ForEach-Object { $_.Name })
  removed_artifacts = @($artifactPaths | ForEach-Object { Split-Path $_ -Leaf })
}

if ($PrintOnly) {
  $output | ConvertTo-Json -Depth 4
  return
}

if ($containerExists) {
  docker rm -f $ContainerName | Out-Null
  $output["removed_container"] = $true
}

foreach ($configFile in $matchingConfigFiles) {
  Remove-Item -Path $configFile.FullName -Force
}

if ($PurgeArtifacts) {
  foreach ($artifactPath in $artifactPaths) {
    Remove-Item -Path $artifactPath -Force
  }
}

$output | ConvertTo-Json -Depth 4
