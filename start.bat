@echo off
setlocal
if not defined PORT set PORT=21435
set PYTHONUNBUFFERED=1
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
python main.py
