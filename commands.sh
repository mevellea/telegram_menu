#!/bin/bash

# Usage: source ./commands.sh && check_all

call_black()
{
  echo "### Call black"
  black . -l 120
}

call_pylint()
{
  echo "### Call pylint"
  pylint telegram_menu tests
}

call_pystyle()
{
  echo "### Call pydocstyle"
  pydocstyle telegram_menu
  echo "### Call pycodestyle"
  pycodestyle --max-line-length=120 telegram_menu
}

call_mypy()
{
  echo "### Call Mypy"
  mypy telegram_menu
}

call_isort()
{
  echo "### Call isort"
  isort -l 120 .
}

# shellcheck disable=SC2120
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

call_demo()
{
  python tests/demo.py
}

call_gendoc()
{
  m2r README.md
  mv README.rst docs
  cp -R resources/ docs/_build/html/
  cd docs || exit
  make html
  cd ..
}

open_doc()
{
  cd docs || exit
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
  call_mypy
  call_pystyle
  call_pylint
  call_coverage
}

call_release()
{
  rm -rf dist
  python -m build
  # python -m twine upload dist/*
  # pip install -U --index-url https://pypi.org/simple/ telegram_menu
}
