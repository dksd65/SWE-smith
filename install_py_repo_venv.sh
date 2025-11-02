#!/bin/bash

# Create virtual environment
python3 -m venv /tmp/testbed_env
source /tmp/testbed_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the repository in editable mode
pip install -e .

# Install testing framework and test dependencies
pip install pytest 'hypothesis>=6.116.0' pytest-xdist

