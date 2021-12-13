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
  pydocstyle .
  echo "### Call pycodestyle"
  pycodestyle --max-line-length=120 .
}

call_mypy()
{
  echo "### Call Mypy"
  mypy --config-file mypy.ini .
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
  python setup.py sdist
  # twine upload dist/*.tar.gz
  # pip install -U --index-url https://pypi.org/simple/ telegram_menu

  # TEST RELEASE
  # twine upload --repository testpypi dist/*.tar.gz
  # pip install -U --index-url https://test.pypi.org/simple/ telegram_menu
}
