# PWSPython

A python module supporting operations related to Partial Wave Spectroscopy.

The ImCube class represents a single 3d (x,y, lambda) pws acquisition and includes methods useful to analysis of pws data.

The reflectance helper can provide the reflectance spectra of any 2 materials included in its library.

The flat field visualizer is intended to show how the pws signal of a thin film acquisition varies accross the field of view.

Utility provides useful function for parallel loading and processing of ImCube files.

## Building from source and distributing
`{blah}` indicates a blank spot named 'blah' that you need to fill in.
Automatic Method:
use the python in your `base` anaconda environment to run `installScripts\build.py`. This will update the version to the `_version` file and run the conda-build and deploy steps.
You will need to have gitpython, and conda-build installed. The version in `setup.py` and pwspy's __version__ variable come from the `_version` file. The `meta.yaml` file for the conda package
creates the version information on it's own from GIT. they should match. It can be understood as `a.b.c.d-xyz` where `a.b.c` are numbers set in the Git tags, `d` is the number of commits since 
`a.b.c` was tagged, `xyz` is the short sha hash for the git commit.

Manual Method:  
Building conda package from source:  
navigate to the root directory of the project and use `conda-build . --output-folder {outputDestination}` to build the package. (You will need to make sure that the `conda-forge` channel is in your `conda.rc` file.
Copy `install.bat` from the `installScripts` folder to `{outputDestination}`. The `{outputDestination}` folder is all that is needed for distribution.


## Automatically installing with the script
Optional:
  Create a new environment with `conda create -n {environmentName}`.
  Add the new environment name to the `env` variable in the first line of `install.bat`.
run the `install.bat`  

## Installing Manually

Optional:
  Create a new environment with `conda create -n {environmentName}`.
  Activate the new environment with `conda activate {environmentName}`.
  
Install the built package with `conda install -c file://{buildDestination} -c conda-forge pwspy`.


