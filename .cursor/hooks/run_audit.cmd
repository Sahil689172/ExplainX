@echo off
REM Cursor hook entry — always exit 0; audit is best-effort side effect
cd /d c:\Users\hp\ExplainX\backend
echo hook_start>%TEMP%\explainx_hook.txt
c:\Users\hp\ExplainX\.venv\Scripts\pythonw.exe c:\Users\hp\ExplainX\backend\_run_audit.py
echo hook_exit_%ERRORLEVEL%>>%TEMP%\explainx_hook.txt
REM Emit minimal JSON for hooks that expect stdout JSON
echo {}
exit /b 0
