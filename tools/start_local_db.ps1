param([ValidateRange(1,65535)][int]$Port=55432)
$ErrorActionPreference='Stop'
# Expected native exit codes (including pg_ctl status=3) are handled explicitly.
$PSNativeCommandUseErrorActionPreference=$false
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPsqlCommand=Get-Command psql.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if(-not $taskPsqlCommand){
    throw "PostgreSQL command-line tools were not found in PATH.`nInstall PostgreSQL 15+ and add its bin directory to PATH,`nor configure an existing PostgreSQL instance via .env."
}
$taskPsql=$taskPsqlCommand.Source
$taskBin=Split-Path -Parent $taskPsql
foreach($taskName in @('initdb.exe','pg_ctl.exe','createdb.exe')){
    if(-not(Test-Path -LiteralPath (Join-Path $taskBin $taskName) -PathType Leaf)){
        throw "PostgreSQL tool $taskName was not found alongside psql.exe. Install the complete PostgreSQL 15+ command-line tools and add their bin directory to PATH, or configure an existing instance via .env."
    }
}
$taskCtl=Join-Path $taskBin 'pg_ctl.exe'
$taskLocal=Join-Path $taskRoot '.local'
$taskData=Join-Path $taskLocal 'pgdata'
$taskLog=Join-Path $taskLocal 'postgres.log'
$taskEnv=Join-Path $taskRoot '.env'
New-Item -ItemType Directory -Force -Path $taskLocal | Out-Null
if(-not(Test-Path -LiteralPath (Join-Path $taskData 'PG_VERSION'))){
    & (Join-Path $taskBin 'initdb.exe') -D $taskData -U horizon --auth=trust --encoding=UTF8 --locale=C
    if($LASTEXITCODE -ne 0){throw 'Project cluster initialization failed. Check PostgreSQL permissions and the .local/pgdata directory.'}
}else{
    Write-Output 'Existing project cluster found; initialization skipped.'
}

$taskStatusOutput=& $taskCtl -D $taskData status 2>&1
$taskStatusCode=$LASTEXITCODE
if($taskStatusCode -eq 0){
    $taskPid=Get-Content -LiteralPath (Join-Path $taskData 'postmaster.pid')
    if($taskPid.Count -lt 6 -or $taskPid[3].Trim() -ne "$Port" -or $taskPid[5].Trim() -ne '127.0.0.1'){
        throw 'The project cluster is already running with a different port or listening address. Use its existing port with -Port and verify that it listens only on 127.0.0.1. No server settings were changed.'
    }
    Write-Output 'Project cluster is already running; startup skipped.'
}elseif($taskStatusCode -eq 3){
    & $taskCtl -D $taskData -l $taskLog -o "-p $Port -h 127.0.0.1" -w start
    if($LASTEXITCODE -ne 0){throw 'Project PostgreSQL startup failed; check .local/postgres.log and whether the selected port is already in use.'}
}else{
    throw "Cannot determine project PostgreSQL status (pg_ctl exit code $taskStatusCode). Check .local/pgdata and PostgreSQL permissions."
}

# Ignore user psql startup files and never prompt for a password in this local trust cluster.
$taskDatabaseExists=& $taskPsql -X -w -h 127.0.0.1 -p $Port -U horizon -d postgres -v ON_ERROR_STOP=1 -Atc "SELECT 1 FROM pg_database WHERE datname='project_horizon'"
if($LASTEXITCODE -ne 0){throw 'Could not check project_horizon in the project cluster. Verify the port and the .local/postgres.log startup log.'}
if(($taskDatabaseExists -join '').Trim() -eq ''){
    & (Join-Path $taskBin 'createdb.exe') -w -h 127.0.0.1 -p $Port -U horizon project_horizon
    if($LASTEXITCODE -ne 0){throw 'Could not create project_horizon in the project cluster.'}
}else{
    Write-Output 'Database project_horizon already exists; creation skipped.'
}
$taskSmoke=& $taskPsql -X -w -h 127.0.0.1 -p $Port -U horizon -d project_horizon -v ON_ERROR_STOP=1 -Atc 'SELECT current_database(), current_user;'
if($LASTEXITCODE -ne 0 -or ($taskSmoke -join '').Trim() -ne 'project_horizon|horizon'){
    throw 'Project database connection smoke test failed. No success status was issued.'
}

if(-not(Test-Path -LiteralPath $taskEnv)){
    @('HORIZON_DB_HOST=127.0.0.1',"HORIZON_DB_PORT=$Port",'HORIZON_DB_NAME=project_horizon','HORIZON_DB_USER=horizon','HORIZON_DB_PASSWORD=') | Set-Content -LiteralPath $taskEnv -Encoding utf8
    $taskEnvStatus='created'
}else{
    $taskEnvStatus='preserved'
    Write-Output 'Existing .env was preserved; no configuration was overwritten.'
    $taskExisting=@{}
    foreach($taskLine in Get-Content -LiteralPath $taskEnv){
        if($taskLine -match '^\s*(HORIZON_DB_(?:HOST|PORT|NAME|USER))\s*=(.*)$'){
            $taskExisting[$Matches[1]]=$Matches[2].Trim()
        }
    }
    if($taskExisting['HORIZON_DB_HOST'] -notin @('127.0.0.1','localhost') -or
       $taskExisting['HORIZON_DB_PORT'] -ne "$Port" -or
       $taskExisting['HORIZON_DB_NAME'] -ne 'project_horizon' -or
       $taskExisting['HORIZON_DB_USER'] -ne 'horizon'){
        Write-Warning 'The preserved .env may point to another database. Review HORIZON_DB_HOST/PORT/NAME/USER before running the pipeline; the helper smoke test used its own project cluster.'
    }
}
Write-Output "PostgreSQL connection smoke test passed: host=127.0.0.1 port=$Port database=project_horizon user=horizon; .env=$taskEnvStatus."
