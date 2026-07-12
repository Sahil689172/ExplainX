@echo off
cd /d c:\Users\hp\ExplainX\backend
echo launch_start>%TEMP%\explainx_audit_launch.txt
c:\Users\hp\ExplainX\.venv\Scripts\python.exe c:\Users\hp\ExplainX\backend\_run_audit.py
echo launch_done_%ERRORLEVEL%>>%TEMP%\explainx_audit_launch.txt
