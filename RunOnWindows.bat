@echo off
setlocal

:: Change directory to the location of the batch file
cd "%~dp0"

:: Create ErrorLogs directory if it doesn't exist
if not exist "ErrorLogs" mkdir "ErrorLogs"

:: Get the current date and time
for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
set datetime=%datetime:~0,4%%datetime:~4,2%%datetime:~6,2%%datetime:~8,2%%datetime:~10,2%%datetime:~12,2%

:: Run the command and redirect errors to the log file
call :RunAndLog pypy "main.py" "ran from %~n0"
pause
exit /b

:RunAndLog
    2>"ErrorLogs\ErrorAt%datetime%.txt" (
        %*
    ) && type "ErrorLogs\ErrorAt%datetime%.txt" || type "ErrorLogs\ErrorAt%datetime%..txt"
    exit /b
