#!/bin/sh
currDir="$(pwd)"
eval "$(conda shell.bash hook)"
conda create -n pwspyEnv -c python=3.8
conda activate pwspyEnv
conda install -c file://"$currDir" -c defaults -c conda-forge pwspy --force-reinstall