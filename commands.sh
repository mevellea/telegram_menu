#!/bin/bash

# Usage: source ./commands.sh && check_all

call_black()
{
  black . -l 120
}

call_pylama()
{
  pylama -o pylama.ini .
}

call_isort()
{
  isort -rc .
}

call_pytest()
{
  pytest -s -W ignore::DeprecationWarning
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
