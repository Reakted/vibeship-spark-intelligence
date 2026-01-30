param(
    [string]$ProjectPath = (Get-Location).Path
)

python -m spark.cli ensure --sync-context --project "$ProjectPath"
