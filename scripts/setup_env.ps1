# RecruitAI Sentinel - Environment Setup Script (Windows Compatible)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RecruitAI Sentinel: Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Ensure script runs from project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($scriptDir) {
    Set-Location $scriptDir
    Set-Location ..
}

# Step 1: Ensure Python version is 3.11
Write-Host "[*] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
$pythonCmd = $null

if ($pythonVersion -match "Python 3.11") {
    Write-Host "[+] Found Python 3.11: $pythonVersion" -ForegroundColor Green
    $pythonCmd = "python"
} else {
    Write-Warning "[-] Python 3.11 is not standard python in PATH. Found: $pythonVersion"
    Write-Host "[*] Attempting to find py -3.11 launcher..." -ForegroundColor Yellow
    $pyVersion = py -3.11 --version 2>&1
    if ($pyVersion -match "Python 3.11") {
        Write-Host "[+] Found py launcher for Python 3.11: $pyVersion" -ForegroundColor Green
        $pythonCmd = "py -3.11"
    } else {
        Write-Error "[-] Python 3.11 not found in PATH or via py launcher. Please install Python 3.11."
        Exit 1
    }
}

# Step 2: Create virtual environment
Write-Host "[*] Creating virtual environment (.venv)..." -ForegroundColor Yellow
Invoke-Expression "$pythonCmd -m venv .venv"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[-] Failed to create virtual environment."
    Exit 1
}
Write-Host "[+] Virtual environment created successfully." -ForegroundColor Green

# Step 3: Upgrade Pip
Write-Host "[*] Upgrading pip inside virtual environment..." -ForegroundColor Yellow
Invoke-Expression ".venv\Scripts\python.exe -m pip install --upgrade pip"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[-] Failed to upgrade pip."
    Exit 1
}
Write-Host "[+] Pip upgraded successfully." -ForegroundColor Green

# Step 4: Install Requirements
Write-Host "[*] Installing Python packages from requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Invoke-Expression ".venv\Scripts\pip.exe install -r requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[-] Package installation failed."
        Exit 1
    }
    Write-Host "[+] All Python packages installed successfully." -ForegroundColor Green
} else {
    Write-Error "[-] requirements.txt not found!"
    Exit 1
}

# Step 5: Create local .env from .env.example
Write-Host "[*] Setting up local .env configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[+] Created local .env file from .env.example." -ForegroundColor Green
    } else {
        Write-Warning "[-] .env.example not found!"
    }
} else {
    Write-Host "[*] .env file already exists. Skipping copy." -ForegroundColor Yellow
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[+] Environment setup completed successfully!" -ForegroundColor Green
Write-Host "[*] Run '.venv\Scripts\Activate.ps1' to activate the environment." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
