@echo off
cd /d c:\Users\hp\ExplainX\backend
echo Running import + script generation tests...
c:\Users\hp\ExplainX\.venv\Scripts\python.exe _run_audit.py
echo.
echo ===== _audit_out.txt =====
type _audit_out.txt
