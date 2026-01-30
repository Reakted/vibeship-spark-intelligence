@echo off
REM Ensure Spark is running for the current project

setlocal
set PROJECT_DIR=%cd%
python -m spark.cli ensure --sync-context --project "%PROJECT_DIR%"
