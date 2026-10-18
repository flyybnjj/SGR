@echo off
title Sistema Municipal La Serena • SGR
cls
echo ======================================================================
echo    ILUSTRE MUNICIPALIDAD DE LA SERENA - PLATAFORMA TERRITORIAL SGR
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=python"
if exist "%SCRIPT_DIR%venv\Scripts\python.exe" set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

echo [1/2] Verificando Servidor Django...
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel% equ 0 (
    echo       [*] El servidor ya esta activo en http://localhost:8000
) else (
    echo       [*] Iniciando servidor Django...
    powershell.exe -NoProfile -Command "Start-Process -FilePath $env:PYTHON_EXE -ArgumentList @('manage.py','runserver','localhost:8000') -WorkingDirectory $env:SCRIPT_DIR -WindowStyle Hidden"
    ping 127.0.0.1 -n 4 >nul
)

echo [2/2] Abriendo navegador...
start "" "http://localhost:8000/login/"

echo.
echo ======================================================================
echo    Acceso Web: http://localhost:8000/login/
echo ======================================================================
echo.
ping 127.0.0.1 -n 3 >nul
exit
