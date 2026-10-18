@echo off
title Sistema Municipal La Serena • SGR
cls
echo ======================================================================
echo    ILUSTRE MUNICIPALIDAD DE LA SERENA - PLATAFORMA TERRITORIAL SGR
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\avalo\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [1/2] Verificando Servidor Django...
netstat -ano | findstr /R /C:":8080 .*LISTENING" >nul
if %errorlevel% equ 0 (
    echo       [*] El servidor ya esta activo en http://127.0.0.1:8080
) else (
    echo       [*] Iniciando servidor Django...
    start "SGR Django Backend" /min cmd /c "cd /d "%SCRIPT_DIR%" && "%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000"
    ping 127.0.0.1 -n 4 >nul
)

echo [2/2] Abriendo navegador...
start "" "http://127.0.0.1:8000/login/"

echo.
echo ======================================================================
echo    Acceso Web: http://127.0.0.1:8080/login/
echo    Credenciales: admin / Admin.2026!
echo ======================================================================
echo.
ping 127.0.0.1 -n 3 >nul
exit
