@echo off
@rem
@rem Executes the code checks.
@rem
call %VENV_PATH%\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements-develop.txt

echo ### Call black
black . -l 120
@if errorlevel 1 echo "<<<### BLACK FAILED #################################################################>>>"

echo ### Call isort
isort -l 120 .
@if errorlevel 1 echo "<<<### ISORT ERROR DETECTED ####################################################>>>"

echo ### Call mypy
if not exist reports mkdir reports
mypy --config-file mypy.ini telegram_menu >%CD%\reports\mypy.txt
@if errorlevel 1 echo "<<<### MYPY PROBLEM DETECTED ########################################################>>>"

echo ### Call pylint
pylint telegram_menu tests -E > %CD%\reports\pylint.txt
@if errorlevel 1 echo "<<<### PYLINT ERROR DETECTED ########################################################>>>"

echo ### Call pydocstyle
pydocstyle . > %CD%\reports\pydocstyle.txt
@if errorlevel 1 echo "<<<### PYDOCSTYLE ERROR DETECTED ####################################################>>>"

echo ### Call pycodestyle
pycodestyle --max-line-length=120 .
@if errorlevel 1 echo "<<<### PYCODESTYLE ERROR DETECTED ####################################################>>>"
