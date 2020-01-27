#!/bin/sh
currDir="$(pwd)"
conda create -n pwspy -c python=3.7
conda activate pwspy
conda install -c file://"$currDir" -c defaults -c conda-forge pwspy --force-reinstall