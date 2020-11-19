#!/bin/sh
eval "$(conda shell.bash hook)"
conda activate pwspyEnv
python -m pwspy.apps.PWSAnalysisApp