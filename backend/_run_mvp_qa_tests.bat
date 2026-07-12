@echo off
cd /d c:\Users\hp\ExplainX\backend
c:\Users\hp\ExplainX\.venv\Scripts\python.exe -m pytest tests/test_quality_assurance.py tests/test_section_generation.py tests/test_single_script_generation.py tests/test_phase36_script_standardization.py tests/test_script_generation.py tests/test_phase3_content_intelligence.py tests/test_circular_imports.py tests/test_prompt_template_format.py tests/test_pipeline_timing.py -q --tb=short
echo EXIT:%ERRORLEVEL%
