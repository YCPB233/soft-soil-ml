#!/usr/bin/env bash
set -e

source ~/anaconda3/etc/profile.d/conda.sh
conda activate cu129_py314_test

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
