# PWSPython

A python module supporting operations related to Partial Wave Spectroscopy.

The ImCube class represents a single 3d (x,y, lambda) pws acquisition and includes methods useful to analysis of pws data.

The reflectance helper can provide the reflectance spectra of any 2 materials included in its library.

The flat field visualizer is intended to show how the pws signal of a thin film acquisition varies accross the field of view.

Utility provides useful function for parallel loading and processing of ImCube files.

## Update Me!!!

Building conda package from source:  
navigate to the root directory of the project and use `conda-build .. --output-folder {outputDestination}` to build the package.

Installing the package using the built conda package
Optional:
  Create a new environment with `conda create -n {environmentName}`.
  Activate the new environment with `conda activate {environmentName}`.

install the built package with `conda install -c file://{buildDestination} pwspy`.

