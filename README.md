# PWSpy
A python module supporting operations related to Partial Wave Spectroscopy.

## Documentation
This project is automatically documented by "Sphinx". If you have Sphinx installed then you can compile documentation to HTML 
by navigating to the `docs` folder and running `make html`. Formats other than HTML are also possible. Documentation is
hosted online at [ReadTheDocs](https://pwspy.readthedocs.io/en/dev/) updating of documentation from the current version on Bitbucket can be performed
by signing into the lab's account at `readthedocs.org`.

## Installation
The first step in installation is to install [Anaconda](https://www.anaconda.com/products/individual) on your computer. Once installation
is completed you will be able to install `PWSpy` by typing commands into the terminal. On Mac and Linux you can use the standard terminal, on Windows you
should open "Anaconda Prompt".
It is advisable to install `PWSpy` into it's own "environment" to avoid dependency conflicts. 
Create a new environment with the command: `conda create -n {environmentName} python=3.7`. You can then make the new environment active in your terminal with `conda activate {environmentName}`.

More information [here](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).

#### Installing from Anaconda Cloud (recommended)
`PWSpy` is stored online on the "backmanlab" Anaconda Cloud channel. It can be installed from Conda with the command `conda install -c conda-forge -c backmanlab pwspy`

#### Installing with the installation helper script
Set the appropriate Conda environment name to the `env` variable in the first line of `install.bat`.
run `install.bat`  

#### Installing Manually
If you have the built package (.tar.gz file) then you can install the package by pointing `conda install` to it.
Install the package with `conda install -c file:///{tarGzFileDestination} -c conda-forge pwspy`.

 
## Building from source and distributing

#### Setting up your computer to build the source code.
First you will need the `Conda` package manager. If you have installed Anaconda then Conda is included.
On Windows you will need to use the `Anaconda Prompt` rather than the default Windows `Command Prompt`.
In addition you will need:  
 - conda-build 
 - anaconda-client 
 - setuptools_scm

These can be installed via: `conda install conda-build anaconda-client setuptools_scm`  

#### Automatic Method (Recommended):
Use the python in your `base` anaconda environment to run `python installScripts\build.py`.
The output will default to `buildscripts/conda/build`. You can optionally provide a custom
output path as the first argument to the `build.py` script. There will be many
files here but the most important one is `build/noarch/pwspy_xxxxxxxxxx.tar.gz`.
This will update the module version in the `_version` file and run the conda-build and deploy steps.
The version number can be understood as `a.b.c.d-xyz` where `a.b.c` are numbers set manually with a Git `Tag`, `d` is the number of commits since 
`a.b.c` was tagged, `xyz` is the short sha hash for the git commit.

#### Uploading a newly built version of the package to Anaconda Cloud
The lab has a `Cloud` account at anaconda.org. The username is `backmanlab` and the password is `UNKNOWN!!!!` (do not put the password here, this git repository is publically available, we prefer not to get hacked).
You can upload the package to the lab's Anaconda Cloud account using `anaconda login` to log into the account and then with `anaconda upload build/noarch/pwspy_xxxxxxxxxx.tar.gz`


