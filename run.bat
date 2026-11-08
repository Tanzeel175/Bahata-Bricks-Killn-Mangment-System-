@echo off
setlocal enabledelayedexpansion
title Bahata Bricks Kiln Management System
cd /d "%~dp0"

echo ===================================================
echo   Bahata Bricks Kiln Management System
echo   Starting Enterprise Desktop ERP...
echo ===================================================
echo.

:: 1. Detect Python Executable
set "PYTHON_EXE="

:: Check if Anaconda exists in user profile
if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
    set "PATH=%USERPROFILE%\anaconda3;%USERPROFILE%\anaconda3\Scripts;%USERPROFILE%\anaconda3\Library\bin;%PATH%"
    goto :FOUND_PYTHON
)

:: Check if standard Python in PATH is valid (not WindowsApps alias)
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    echo "%%i" | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set "PYTHON_EXE=%%i"
        goto :FOUND_PYTHON
    )
)

:: Check Python Launcher (py.exe)
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    goto :FOUND_PYTHON
)

:: Check localappdata Python
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set "PYTHON_EXE=%%d\python.exe"
        set "PATH=%%d;%%d\Scripts;!PATH!"
        goto :FOUND_PYTHON
    )
)

:: Check Program Files Python
for /d %%d in ("C:\Program Files\Python*") do (
    if exist "%%d\python.exe" (
        set "PYTHON_EXE=%%d\python.exe"
        set "PATH=%%d;%%d\Scripts;!PATH!"
        goto :FOUND_PYTHON
    )
)

:FOUND_PYTHON
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system.
    echo Please install Python from https://www.python.org/downloads/
    echo or ensure Anaconda / Python is installed.
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_EXE%
echo [OK] Launching Application...
echo.

%PYTHON_EXE% -m app.main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with code %errorlevel%.
    pause
)