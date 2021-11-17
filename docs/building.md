#### Setting up your computer to build the Conda package.
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
The lab has a `Cloud` account at anaconda.org, the channel name is`backmanlab`.
You can upload the package to the lab's Anaconda Cloud account using `anaconda login` to log into the account and then with `anaconda upload build/noarch/pwspy_xxxxxxxxxx.tar.gz`
