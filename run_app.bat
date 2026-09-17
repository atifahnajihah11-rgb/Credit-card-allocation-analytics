@echo off

set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Anaconda Python could not be found.
    echo Expected location: %PYTHON_EXE%
    pause
    exit /b 1
)

cd /d "%~dp0"
"%PYTHON_EXE%" app.py

if errorlevel 1 (
    echo.
    echo The application stopped because of an error.
    pause
)