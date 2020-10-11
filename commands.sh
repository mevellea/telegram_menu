#!/bin/bash

# Usage: source ./commands.sh && check_all

call_black()
{
  black . -l 120
}

call_pylama()
{
  pylama -o pylama.ini telegram_menu
  pylama -o pylama.ini tests
}

call_mypy()
{
  mypy --config-file mypy.ini .
}

call_isort()
{
  isort -rc .
}

call_coverage()
{
  coverage run --source=telegram_menu -m pytest -s -W ignore::DeprecationWarning
  coverage html
  if [ "$2" = true ] ; then
    firefox htmlcov/index.html
  fi
  coverage report
}

call_pyreverse()
{
  pyreverse --output=png --filter-mode=PUB_ONLY telegram_menu
}

call_gendoc()
{
  m2r README.md
  mv README.rst docs
  cp -R resources/ docs/_build/html/
  cd docs || exit
  make html
  xdg-open _build/html/index.html &
  cd ..
}

start_venv()
{
  VENV_NAME=venv_home
  VENV_PATH=~/$VENV_NAME
  echo "Activating virtual environment $VENV_PATH"
  source $VENV_PATH/bin/activate
}

call_check()
{
  start_venv
  call_isort
  call_black
  call_pylama
  call_mypy
  call_coverage
}
