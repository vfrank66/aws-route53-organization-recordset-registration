#!/usr/bin/env bash

# Exit virtualenv if in one
deactivate &>/dev/null
set -e

DOES_VENV_EXIST=0
if [[ -d "./venv/" ]]; then
    DOES_VENV_EXIST=1
fi

# Install and setup virtualenv
python3.9 -m pip install --upgrade pip
python3.9 -m pip install --user virtualenv
python3.9 -m venv venv

# activate the virtualenv
if [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi 

# if the virtualenv already exists this will update the pip
# after it has been activated
if [[ ${DOES_VENV_EXIST} == 1 ]]; then
    echo "Upgrading pip within the virtualenv"
    python3.9 -m pip install --upgrade pip
fi

pip3.9 install -r requirements-dev.txt  