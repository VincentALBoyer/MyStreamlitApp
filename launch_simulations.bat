@echo off
setlocal
cd /d "%~dp0"

:menu
cls
echo ======================================================
echo    Logistics Information Systems - Simulation Suite
echo ======================================================
echo.
echo Please select the application to launch:
echo.
echo [1] CRM App (Customer Relationship Management)
echo [2] SRM App (Supplier Relationship Management)
echo [3] ERP App (Enterprise Resource Planning)
echo [4] Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto launch_crm
if "%choice%"=="2" goto launch_srm
if "%choice%"=="3" goto launch_erp
if "%choice%"=="4" goto end

echo Invalid choice, try again.
pause
goto menu

:launch_crm
echo Launching CRM App...
.venv_test\Scripts\python.exe -m streamlit run CRM_App\app.py
goto menu

:launch_srm
echo Launching SRM App...
.venv_test\Scripts\python.exe -m streamlit run SRM_App\app.py
goto menu

:launch_erp
echo Launching ERP App...
.venv_test\Scripts\python.exe -m streamlit run ERP_App\app.py
goto menu

:end
echo Goodbye!
pause
exit
