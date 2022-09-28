@echo off

cd %~dp0

set ANSICON=on

rem call ..\venv\Scripts\activate

python .\manage.py runserver 0.0.0.0:8000

pause
