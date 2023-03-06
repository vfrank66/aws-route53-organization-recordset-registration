#!/usr/bin/env bash
set -e

pushd ..

black --line-length 120 --target-version py39 src tests
yapf --in-place --recursive setup.py src tests
docformatter --in-place --recursive setup.py src tests
echo 'Running isort'
isort -rc --line-width 120 src tests
echo 'Running pydocstyle'
pydocstyle src/ --add-ignore=D100,D202,D204,D205,D209,D400,D403,D402
echo 'Running mypy'
mypy --ignore-missing-imports src
echo 'Running flake8'
flake8 setup.py src