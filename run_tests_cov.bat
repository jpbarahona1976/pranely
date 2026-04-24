@echo off
cd /d C:\Projects\Pranely\packages\backend
C:\Users\barah\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install pytest-cov --quiet
C:\Users\barah\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests\test_backup_dr.py -v --tb=short --cov=tests --cov-report=xml --cov-report=html --cov-report=term-missing
