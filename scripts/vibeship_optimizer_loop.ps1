param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("start","finish")]
  [string]$Phase,

  [string]$Title = "",
  [string]$ChangeId = "",
  [int]$Rounds = 80
)

$ErrorActionPreference = "Stop"

function Invoke-VO {
  # Avoid PowerShell's automatic $Args variable by using a different name.
  param([string[]]$CliArgs)
  & python -m vibeship_optimizer @CliArgs
  if ($LASTEXITCODE -ne 0) { throw "vibeship-optimizer failed: $($CliArgs -join ' ')" }
}

function Ensure-Dir([string]$Path) {
  if (!(Test-Path $Path)) { New-Item -ItemType Directory -Force $Path | Out-Null }
}

function Extract-JsonBlock {
  param([string[]]$Lines)
  $start = -1
  $end = -1
  for ($i = 0; $i -lt $Lines.Count; $i++) {
    if ($start -lt 0 -and $Lines[$i] -match '^\s*\{\s*$') { $start = $i }
    if ($Lines[$i] -match '^\s*\}\s*$') { $end = $i }
  }
  if ($start -lt 0 -or $end -lt 0 -or $end -lt $start) { return $null }
  return ($Lines[$start..$end] -join "`n")
}

Ensure-Dir "reports/optimizer"

Invoke-VO @("init")

if ($Phase -eq "start") {
  if (-not $Title) { throw "Phase=start requires -Title" }

  if (-not $ChangeId) {
    $raw = & python -m vibeship_optimizer change start --title $Title
    if ($LASTEXITCODE -ne 0) { throw "change start failed" }
    # The CLI prints "Initialized: ..." lines then pretty-printed JSON.
    $jsonBlock = Extract-JsonBlock -Lines $raw
    if (-not $jsonBlock) { throw "change start did not return a JSON block" }
    $obj = $jsonBlock | ConvertFrom-Json
    $ChangeId = [string]$obj.change_id
  }

  $preflightOut = "reports/optimizer/$ChangeId`_preflight.md"
  Invoke-VO @("preflight","--change-id",$ChangeId,"--out",$preflightOut)

  $beforeSnap = & python -m vibeship_optimizer snapshot --label "$ChangeId-before"
  if ($LASTEXITCODE -ne 0) { throw "snapshot(before) failed" }
  $beforeSnap = ($beforeSnap | Select-Object -Last 1).Trim()
  Set-Content -Encoding ascii -Path "reports/optimizer/$ChangeId`_before.path" -Value $beforeSnap
  Copy-Item -Force $beforeSnap "reports/optimizer/$ChangeId`_before_snapshot.json"

  Write-Host ("change_id=" + $ChangeId)
  Write-Host ("before_snapshot=" + $beforeSnap)
  Write-Host ("next=make one optimization commit, then run: .\\scripts\\vibeship_optimizer_loop.ps1 -Phase finish -ChangeId " + $ChangeId)
  exit 0
}

if ($Phase -eq "finish") {
  if (-not $ChangeId) { throw "Phase=finish requires -ChangeId" }

  $beforePathFile = "reports/optimizer/$ChangeId`_before.path"
  if (!(Test-Path $beforePathFile)) { throw "Missing $beforePathFile (run Phase=start first)" }
  $beforeSnap = (Get-Content $beforePathFile -Raw).Trim()
  if (-not $beforeSnap) { throw "Empty before snapshot path in $beforePathFile" }

  $afterSnap = & python -m vibeship_optimizer snapshot --label "$ChangeId-after"
  if ($LASTEXITCODE -ne 0) { throw "snapshot(after) failed" }
  $afterSnap = ($afterSnap | Select-Object -Last 1).Trim()
  Set-Content -Encoding ascii -Path "reports/optimizer/$ChangeId`_after.path" -Value $afterSnap
  Copy-Item -Force $afterSnap "reports/optimizer/$ChangeId`_after_snapshot.json"

  $cmpMd = "reports/optimizer/$ChangeId`_compare.md"
  $cmpJson = "reports/optimizer/$ChangeId`_compare.json"
  Invoke-VO @("compare","--before",$beforeSnap,"--after",$afterSnap,"--out",$cmpMd,"--json-out",$cmpJson)

  # Spark critical-path KPI capture (advisory speed + delivery).
  $deltaOut = "reports/optimizer/$ChangeId`_advisory_delta.json"
  & python scripts/advisory_controlled_delta.py --rounds $Rounds --label $ChangeId --force-live --out $deltaOut | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "advisory_controlled_delta failed" }

  # Self-evolution KPI capture (packet reuse / exact hit rate) - allow packet store lookups.
  $deltaCachedOut = "reports/optimizer/$ChangeId`_advisory_delta_cached.json"
  & python scripts/advisory_controlled_delta.py --rounds $Rounds --label $ChangeId --out $deltaCachedOut | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "advisory_controlled_delta(cached) failed" }

  Write-Host ("change_id=" + $ChangeId)
  Write-Host ("after_snapshot=" + $afterSnap)
  Write-Host ("compare_md=" + $cmpMd)
  Write-Host ("advisory_delta=" + $deltaOut)
  Write-Host ("advisory_delta_cached=" + $deltaCachedOut)
  exit 0
}

throw "Unknown -Phase: $Phase"
