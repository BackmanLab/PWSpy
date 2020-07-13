# PWSPython

A python module supporting operations related to Partial Wave Spectroscopy.

## Documentation
This project is automatically documented by Sphinx. If you have Sphinx installed then you can compile documentation to HTML. 
by navigating to the `docs` folder and running `make html`. Formats other than HTML are also possible. Documentation is
hosted online at `https://pwspy.readthedocs.io/en/dev/` updating of documentation from the current version on Bitbucket can be performed
by signing into the lab's account at `readthedocs.org`.

## Setting up your computer to build the source code.
First you will need the `Conda` package manager. If you have installed Anaconda then Conda is included.
On Windows you will need to use the `Anaconda Prompt` rather than the default Windows `Command Prompt`.
In addition you will need:
 - conda-build: `conda install conda-build`
 - anaconda-client: `conda install anaconda-client`
 - gitpython: `conda install -c conda-forge gitpython`
 
## Building from source and distributing

### Automatic Method (Recommended):
use the python in your `base` anaconda environment to run `installScripts\build.py`. Provide the output path as the first argument. For example if you want to save the built code to the H: drive you would type `python build.py H:`.
This will update the module version in the `_version` file and run the conda-build and deploy steps. Note: You will need to have `conda-build` and `gitpython` installed in your `base` environment.
The version in `setup.py` and pwspy's __version__ variable are loaded from the `_version` file. The `meta.yaml` file for the conda package
creates the version information on it's own from Git. They should match. The version number can be understood as `a.b.c.d-xyz` where `a.b.c` are numbers set with a Git `Tag`, `d` is the number of commits since 
`a.b.c` was tagged, `xyz` is the short sha hash for the git commit. If no output path argument is provided to the build command (`python build.py`) then the built package will default to `buildscripts/conda/build`. There will be many
files here but the most important one is `build/noarch/pwspy_xxxxxxxxxx.tar.gz`.

### Manual Method:  
You will need to update the `_version` file on your own, this can be done by simply running `import pwspy` in python in an environment that has `gitpython` installed. Next, navigate to the root directory of the project and use `conda-build . --output-folder build -c conda-forge` to build the package. The package will appear as a .tar.gz file in the `build/noarch` directory.
Copy `install.bat` from the `installScripts` folder to `{outputDestination}`. The `{outputDestination}` folder is all that is needed for distribution.

### Uploading a built version of the package to Anaconda Cloud
The lab has a `Cloud` account at anaconda.org. The username is `backmanlab` and the password is `UNKNOWN!!!!` (do not put the password here, this git repository is publically available, we prefer not to get hacked).
You can upload the package to the lab's Anaconda Cloud account using `anaconda login` to log into the account and then with `anaconda upload build/noarch/pwspy_xxxxxxxxxx.tar.gz`

## Installation
If you use Conda to work on other projects then it is advisable to install `pwspy` into it's own "environment" to avoid dependency conflicts. 
Create a new environment with `conda create -n {environmentName} python=3.7`. You can then make the new environment active in your terminal with `conda activate {environmentName}`.

More information here: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

### Installing from the backmanlab Anaconda channel
`pwspy` is stored online on the lab's Anaconda Cloud account. It can be installed from Conda with the command `conda install -c conda-forge -c backmanlab pwspy`

### Installing with the installtion helper script
Set the appropriate Conda environment name to the `env` variable in the first line of `install.bat`.
run `install.bat`  

### Installing Manually
If you have the built package (.tar.gz file) then you can install the package by pointing `conda install` to the it.
Install the package with `conda install -c file:///{tarGzFileDestination} -c conda-forge pwspy`.


