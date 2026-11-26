<#
.SYNOPSIS
    K-MDS 개발 환경 준비: 도구 설치(winget) → 의존성 설치 → 테스트.

.DESCRIPTION
    인자 없이 실행하면 설치 여부만 점검하고 아무것도 설치하지 않는다.
    -InstallTools 를 주면 없는 도구를 winget 으로 설치한다(사용자 범위가 아닌 도구는 UAC 승인 창이 뜬다).
    도구가 갖춰진 범위까지만 의존성 설치와 테스트를 수행하고, 없는 도구의 단계는 SKIP 으로 표시한다.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1                 # 점검만
    powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -InstallTools   # 설치 + 의존성 + 테스트
    powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -InstallTools -Only uv   # Python 쪽만
#>
param(
    [switch]$InstallTools,      # 없는 도구를 winget 으로 설치
    [switch]$IncludeDocker,     # Docker Desktop 도 설치 대상에 포함(재부팅·WSL2 필요할 수 있음)
    [switch]$SkipDeps,          # 의존성 설치 생략
    [switch]$SkipTests,         # 테스트 생략
    [string[]]$Only             # 대상 도구 제한: uv, node, java, dotnet, docker
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Results = New-Object System.Collections.Generic.List[object]

# 도구 목록. Python 은 uv 가 필요한 버전(3.11, 3.12)을 직접 내려받으므로 따로 설치하지 않는다.
$Tools = @(
    @{ Key = 'uv';     Name = 'uv (Python 3.11/3.12 포함 관리)'; WingetId = 'astral-sh.uv';                    Check = { [bool](Get-Command uv -ErrorAction SilentlyContinue) } },
    @{ Key = 'node';   Name = 'Node.js LTS (npm 포함)';          WingetId = 'OpenJS.NodeJS.LTS';               Check = { [bool](Get-Command npm -ErrorAction SilentlyContinue) } },
    @{ Key = 'java';   Name = 'JDK 21 (Temurin)';                WingetId = 'EclipseAdoptium.Temurin.21.JDK';  Check = { [bool](Get-Command java -ErrorAction SilentlyContinue) } },
    @{ Key = 'dotnet'; Name = '.NET SDK 10';                     WingetId = 'Microsoft.DotNet.SDK.10';         Check = { (Get-Command dotnet -ErrorAction SilentlyContinue) -and ((& dotnet --list-sdks 2>$null) -match '^10\.') } },
    @{ Key = 'docker'; Name = 'Docker Desktop (선택)';           WingetId = 'Docker.DockerDesktop';            Check = { [bool](Get-Command docker -ErrorAction SilentlyContinue) }; Optional = $true }
)

function Update-SessionPath {
    # winget 설치 직후 새 PATH 를 현재 세션에 반영한다.
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user;$env:USERPROFILE\.local\bin"
    $javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine')
    if ($javaHome) { $env:JAVA_HOME = $javaHome }
}

function Test-Selected($key) { (-not $Only) -or ($Only -contains $key) }

function Add-Result($area, $step, $status, $note = '') {
    $Results.Add([pscustomobject]@{ Area = $area; Step = $step; Status = $status; Note = $note })
}

function Invoke-Step($area, $step, $dir, [scriptblock]$action) {
    Write-Host ""
    Write-Host "=== [$area] $step" -ForegroundColor Cyan
    Push-Location (Join-Path $RepoRoot $dir)
    try {
        $global:LASTEXITCODE = 0
        # 호출 쪽에서 반환값을 버려도(Out-Null) 명령 출력은 화면·로그에 남도록 Out-Host 로 보낸다.
        & $action | Out-Host
        if ($LASTEXITCODE -eq 0) { Add-Result $area $step 'PASS'; return $true }
        Add-Result $area $step 'FAIL' "exit $LASTEXITCODE"; return $false
    } catch {
        Add-Result $area $step 'FAIL' $_.Exception.Message; return $false
    } finally {
        Pop-Location
    }
}

# ---------------------------------------------------------------- 1. 도구
Write-Host "=== 1. 도구 점검" -ForegroundColor Cyan
Update-SessionPath
$Have = @{}
foreach ($t in $Tools) {
    $ok = [bool](& $t.Check)
    $wanted = (Test-Selected $t.Key) -and ((-not $t.Optional) -or $IncludeDocker)
    if (-not $ok -and $wanted -and $InstallTools) {
        Write-Host "설치: $($t.Name)  [winget $($t.WingetId)]" -ForegroundColor Yellow
        winget install --id $t.WingetId -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
        Update-SessionPath
        $ok = [bool](& $t.Check)
        if (-not $ok) { Write-Host "  설치 후에도 명령을 찾지 못했다. 새 터미널에서 다시 실행해 본다." -ForegroundColor Red }
    }
    $Have[$t.Key] = $ok
    $state = if ($ok) { '있음' } elseif ($wanted) { '없음' } else { '없음(대상 아님)' }
    Write-Host ("  {0,-34} {1,-16} winget: {2}" -f $t.Name, $state, $t.WingetId)
}

if (-not $InstallTools -and ($Have.Values -contains $false)) {
    Write-Host ""
    Write-Host "없는 도구는 -InstallTools 를 붙여 다시 실행하면 설치한다." -ForegroundColor Yellow
}

# ---------------------------------------------------------------- 2. 의존성
$Deps = @{}
if (-not $SkipDeps) {
    if ($Have.uv -and (Test-Selected 'uv')) {
        $Deps.root      = Invoke-Step 'k-mds(루트)' '의존성 uv sync --locked' '.' { uv sync --locked }
        # validator 는 Python 버전 고정이 없어 uv 가 최신(3.15)을 고르면 pydantic-core wheel 이 없어 빌드에 실패한다.
        $Deps.validator = Invoke-Step 'validator' '의존성 uv sync --locked --python 3.12' 'apps/imo-compendium-mapping-validator' { uv sync --locked --python 3.12 }
        $Deps.agent     = Invoke-Step 'ghg-agent' '의존성 uv sync --locked --python 3.12' 'apps/kr-ghg-ai-agent' { uv sync --locked --python 3.12 }
        # data-space/python 의 .python-version 은 특정 PC 의 절대경로라서 버전을 명시한다.
        $Deps.dsPython  = Invoke-Step 'data-space/python' '의존성 uv sync --locked --python 3.12' 'apps/data-space/python' { uv sync --locked --python 3.12 }
    } elseif (Test-Selected 'uv') { Add-Result 'Python 4종' '의존성' 'SKIP' 'uv 없음' }

    if ($Have.node -and (Test-Selected 'node')) {
        $Deps.dsNode = Invoke-Step 'data-space(n8n 노드)' '의존성 npm ci' 'apps/data-space' { npm ci }
        $Deps.dsJs   = Invoke-Step 'data-space/javascript' '의존성 npm ci' 'apps/data-space/javascript/ship-odms' { npm ci }
    } elseif (Test-Selected 'node') { Add-Result 'data-space/javascript' '의존성' 'SKIP' 'Node.js 없음' }

    if ($Have.java -and (Test-Selected 'java')) {
        $Deps.java = Invoke-Step 'data-space/java' '의존성 gradlew assemble' 'apps/data-space/java/ship_odms' { .\gradlew.bat --no-daemon assemble }
    } elseif (Test-Selected 'java') { Add-Result 'data-space/java' '의존성' 'SKIP' 'JDK 21 없음' }

    if ($Have.dotnet -and (Test-Selected 'dotnet')) {
        $Deps.dotnet = Invoke-Step 'data-space/dotnet' '의존성 dotnet restore' 'apps/data-space/dotnet/ship_odms' { dotnet restore }
    } elseif (Test-Selected 'dotnet') { Add-Result 'data-space/dotnet' '의존성' 'SKIP' '.NET SDK 10 없음' }
}

# ---------------------------------------------------------------- 3. 테스트
if (-not $SkipTests) {
    if ($Have.uv -and (Test-Selected 'uv')) {
        # 루트: CI(.github/workflows/ci.yml)와 같은 순서
        Invoke-Step 'k-mds(루트)' '비밀정보 검사' '.' { uv run python scripts/check_secrets.py --all } | Out-Null
        Invoke-Step 'k-mds(루트)' 'build' '.' { uv run python scripts/dev.py build } | Out-Null
        Invoke-Step 'k-mds(루트)' 'validate (Ruff+MyPy+Pytest)' '.' { uv run python scripts/dev.py validate } | Out-Null

        Invoke-Step 'validator' 'pytest' 'apps/imo-compendium-mapping-validator' { uv run pytest -q } | Out-Null

        $agent = 'apps/kr-ghg-ai-agent'
        # 순서: registry(FAL50 xlsx 필요) → 후보 집합(var/candidate-inventory.json) → 테스트.
        # 둘 중 하나라도 없으면 unit·contract·integration 다수가 건너뛰거나 실패한다.
        $env:PYTHONUTF8 = '1'
        # prepare_registry.py 는 이미 적재된 DB 에 다시 돌리면 VERSION_ALREADY_LOADED 로 실패하므로 없을 때만 만든다.
        $agentVar = Join-Path $RepoRoot "$agent/var"
        $registry = $true
        if (Test-Path (Join-Path $agentVar 'registry.sqlite3')) { Add-Result 'ghg-agent' 'registry 준비' 'PASS' '이미 있음' }
        else { $registry = Invoke-Step 'ghg-agent' 'registry 준비' $agent { uv run python tools/prepare_registry.py } }
        if ($registry) {
            if (Test-Path (Join-Path $agentVar 'candidate-inventory.json')) { Add-Result 'ghg-agent' '후보 집합 생성' 'PASS' '이미 있음' }
            else { $registry = Invoke-Step 'ghg-agent' '후보 집합 생성' $agent { uv run python tools/build_candidate_inventory.py } }
        }
        Invoke-Step 'ghg-agent' 'pytest unit+contract' $agent { uv run pytest tests/unit tests/contract -q } | Out-Null
        if ($registry) {
            Invoke-Step 'ghg-agent' 'pytest integration' $agent { uv run pytest tests/integration -q } | Out-Null
        } else { Add-Result 'ghg-agent' 'pytest integration' 'SKIP' 'registry 준비 실패' }
        Invoke-Step 'ghg-agent' 'ruff' $agent { uv run ruff check src tools tests } | Out-Null
        Invoke-Step 'ghg-agent' 'mypy' $agent { uv run mypy src } | Out-Null
    } elseif (Test-Selected 'uv') { Add-Result 'Python 3종' '테스트' 'SKIP' 'uv 없음' }

    if ($Have.node -and (Test-Selected 'node')) {
        $js = 'apps/data-space/javascript/ship-odms'
        Invoke-Step 'data-space/javascript' 'eslint' $js { npm run lint } | Out-Null
        Invoke-Step 'data-space/javascript' 'vite build' $js { npm run build } | Out-Null
    } elseif (Test-Selected 'node') { Add-Result 'data-space/javascript' '테스트' 'SKIP' 'Node.js 없음' }

    if ($Have.java -and (Test-Selected 'java')) {
        Invoke-Step 'data-space/java' 'gradlew test' 'apps/data-space/java/ship_odms' { .\gradlew.bat --no-daemon test } | Out-Null
    } elseif (Test-Selected 'java') { Add-Result 'data-space/java' '테스트' 'SKIP' 'JDK 21 없음' }

    if ($Have.dotnet -and (Test-Selected 'dotnet')) {
        # 테스트 프로젝트가 없어 빌드 성공 여부만 본다.
        Invoke-Step 'data-space/dotnet' 'dotnet build' 'apps/data-space/dotnet/ship_odms' { dotnet build --nologo } | Out-Null
    } elseif (Test-Selected 'dotnet') { Add-Result 'data-space/dotnet' '테스트' 'SKIP' '.NET SDK 10 없음' }
}

# ---------------------------------------------------------------- 요약
Write-Host ""
Write-Host "=== 요약" -ForegroundColor Cyan
$Results | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
$failed = @($Results | Where-Object Status -eq 'FAIL').Count
$skipped = @($Results | Where-Object Status -eq 'SKIP').Count
Write-Host "FAIL $failed / SKIP $skipped / 전체 $($Results.Count)"
if ($failed -gt 0) { exit 1 }
exit 0
