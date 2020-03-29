#!/bin/bash

# Usage: source ./commands.sh && check_all

call_black()
{
  black telegram_menu -l 120
}

call_pylama()
{
  pylama -o pylama.ini telegram_menu
}

call_isort()
{
  isort -rc telegram_menu
}

call_pytest()
{
  pytest -s -W ignore::DeprecationWarning
}

call_coverage_report()
{
  coverage run --source=telegram_menu -m pytest -s -W ignore::DeprecationWarning
  coverage html
  firefox htmlcov/index.html
  coverage report
}

call_pyreverse()
{
  pyreverse --output=png --filter-mode=PUB_ONLY telegram_menu
}

check_all()
{
  start_venv
  call_black
  call_pylama
  call_pytest
}

start_venv()
{
  VENV_NAME=venv_home
  VENV_PATH=~/$VENV_NAME
  echo "Activating virtual environment $VENV_PATH"
  source $VENV_PATH/bin/activate
}
