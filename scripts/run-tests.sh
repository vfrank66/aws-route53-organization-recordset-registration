#!/usr/bin/env bash
set -ex

./validations.sh

cd ..
echo 'Running pip install'
pip3.9 install .
echo 'Running pytest'
python3.9 -m pytest -s --junitxml=pytest-report.xml --cov-report html --cov-report term-missing --cov-branch --cov=src

echo 'Running `pip check` to determine if installed packages have compatible dependancies'
pip3.9 check

cd scripts