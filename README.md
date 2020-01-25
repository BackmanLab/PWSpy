# PWSPython

A python module supporting operations related to Partial Wave Spectroscopy.

#Documentation
This project is automatically documented by Sphinx.

## Setting up your computer to build the source code.
First you will need the `Conda` package manager. If you have installed Anaconda then Conda is included.
On Windows you will need to use the `Anaconda Prompt` rather than the defualt Windows `Command Prompt`.
In addition you will need:
 - conda-build: `conda install conda-build`
 - anaconda-client: `conda install anaconda-client`
 - gitpython: `conda install -c conda-forge gitpython`
 
## Building from source and distributing
### Automatic Method (Recommended):
use the python in your `base` anaconda environment to run `installScripts\build.py`. Provide the output path as the first argument. For example if you want to save the built code to the H: drive you would type `python build.py H:`.
This will update the version to the `_version` file and run the conda-build and deploy steps.
The version in `setup.py` and pwspy's __version__ variable come from the `_version` file. The `meta.yaml` file for the conda package
creates the version information on it's own from Git. They should match. The version number can be understood as `a.b.c.d-xyz` where `a.b.c` are numbers set with a Git `Tag`, `d` is the number of commits since 
`a.b.c` was tagged, `xyz` is the short sha hash for the git commit.

### Manual Method:  
You will need to update the `_version` file on your own. Next, navigate to the root directory of the project and use `conda-build . --output-folder build -c conda-forge` to build the package. The package will appear as a .tar.gz file in the `build/noarch` directory.
Copy `install.bat` from the `installScripts` folder to `{outputDestination}`. The `{outputDestination}` folder is all that is needed for distribution.
The lab has a `Cloud` account at anaconda.org. The username is `backmanlab` and the password is `UNKNOWN!!!!`.
You can upload the package to the lab's Anaconda Cloud account using `anaconda login` to log into the account and then with `anaconda upload build/noarch/pwspy_xxxxxxxxxx.tar.gz`


## Automatically installing with the script
Python 3.7 or greater is required.
Optional:
  Create a new environment with `conda create -n {environmentName} -c python=3.7`.
  Add the new environment name to the `env` variable in the first line of `install.bat`.
run the `install.bat`  

## Additional Install Methods

### Installing from Anaconda Cloud
If you have conda installed then you can install the package with the following command: `conda install -c backmanlab -c conda-forge pwspy`

### Installing Manually
If you have the built package then you can install the package by pointing `conda install` to the it.
Install the package with `conda install -c file://{buildDestination} -c conda-forge pwspy`.


