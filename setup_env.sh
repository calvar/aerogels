#!/usr/bin/env bash
# Creates/updates the project's Python virtual environment (.venv) with
# everything needed to run the notebooks under reproduce_paper/:
#   - reproduce_paper/rand_packing/rcpgen_examples.ipynb  (rcpgenerator)
#   - reproduce_paper/tessellation/pyvoro2examples.ipynb  (pyvoro2 + viz)
#
# Usage: ./setup_env.sh
#
# Requirements to build rcpgenerator from source: git, cmake, a C++17
# compiler with OpenMP (gcc/g++ on Linux is fine).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"
RCPGEN_REPO="https://github.com/KD-physics/RCPGenerator.git"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

if [ ! -d "$VENV_DIR" ]; then
    echo ">> Creating virtual environment in $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ">> Upgrading pip tooling"
python -m pip install --upgrade pip setuptools wheel

echo ">> Installing requirements.txt (numpy, pyvoro2[viz], jupyter, ...)"
python -m pip install -r requirements.txt

echo ">> Fetching and building rcpgenerator from source (no PyPI wheels yet)"
git clone --depth 1 "$RCPGEN_REPO" "$BUILD_DIR/RCPGenerator"
python -m pip install -v "$BUILD_DIR/RCPGenerator/python_code/python"

echo ">> Registering Jupyter kernel 'aerogels'"
python -m ipykernel install --user --name aerogels --display-name "Python (aerogels)"

echo ">> Done. Activate with: source $VENV_DIR/bin/activate"
echo ">> In Jupyter/VS Code, select the 'Python (aerogels)' kernel to run the notebooks."
