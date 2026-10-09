$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPython=if($env:HORIZON_PYTHON){$env:HORIZON_PYTHON}elseif(Test-Path -LiteralPath (Join-Path $taskRoot '.venv/Scripts/python.exe')){Join-Path $taskRoot '.venv/Scripts/python.exe'}else{'python'}
& $taskPython (Join-Path $PSScriptRoot 'build_github_release.py')
if($LASTEXITCODE -ne 0){throw 'Release build or validation failed'}
