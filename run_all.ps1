<#
.SYNOPSIS
Run Project Horizon with an explicit Fast/Full scale and optional engine/stage.
.DESCRIPTION
Exactly one of Fast/Full is required. PythonOnly/WolframOnly and
GenerateOnly/AnalyzeOnly are separate mutually exclusive groups.
GenerateOnly ignores language selection and prefers licensed Wolfram.
.EXAMPLE
./run_all.ps1 -Fast -PythonOnly
.EXAMPLE
./run_all.ps1 -Full -AnalyzeOnly -PythonOnly
#>
param([switch]$Fast,[switch]$Full,[switch]$PythonOnly,[switch]$WolframOnly,
      [switch]$GenerateOnly,[switch]$AnalyzeOnly)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
if([bool]$Fast -eq [bool]$Full){throw 'Exactly one of -Fast / -Full is required.'}
if($PythonOnly -and $WolframOnly){throw 'PythonOnly and WolframOnly are mutually exclusive.'}
if($GenerateOnly -and $AnalyzeOnly){throw 'GenerateOnly and AnalyzeOnly are mutually exclusive.'}
Set-Location $PSScriptRoot
if(-not $env:HORIZON_PYTHON -and (Test-Path -LiteralPath '.env')){
    foreach($taskLine in Get-Content -LiteralPath '.env'){
        if($taskLine -match '^\s*HORIZON_PYTHON\s*=(.+)$'){$env:HORIZON_PYTHON=$Matches[1].Trim()}
    }
}
$taskPython=if($env:HORIZON_PYTHON){$env:HORIZON_PYTHON}elseif(Test-Path -LiteralPath '.venv/Scripts/python.exe'){(Resolve-Path '.venv/Scripts/python.exe').Path}else{'python'}
$taskArgs=@('-m','python_src.runner',$(if($Full){'--full'}else{'--fast'}))
if($PythonOnly){$taskArgs+='--python-only'}
if($WolframOnly){$taskArgs+='--wolfram-only'}
if($GenerateOnly){$taskArgs+='--generate-only'}
if($AnalyzeOnly){$taskArgs+='--analyze-only'}
& $taskPython @taskArgs
exit $LASTEXITCODE
