from git import Repo
import os
import shutil
import subprocess

"""This builds the pwpsy conda package and saves it to `outputDir`
It should be run from the base conda env."""

outputDir = 'I:'

buildScriptDir = os.path.dirname(os.path.abspath(__file__)) #Location of build scripts
buildDir = os.path.split(buildScriptDir)[0] #Parent directory of project.

# Set the version number of the package. this should be shared by the package itself, the setup.py file, and the conda package `yaml`
repo = Repo(buildDir)
version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
pwspydir = os.path.join(repo.working_tree_dir, 'src', 'pwspy')
with open(os.path.join(pwspydir, '_version'), 'w') as f: #Overwrite the version file
    f.write(version)

# Build and save to the outputDirectory

proc = subprocess.Popen(f"conda-build {buildDir} --output-folder {outputDir}", stdin=None, stderr=None)
print("Waiting for conda-build")
proc.wait()
result, error = proc.communicate()
if error: print(f"conda-build Error: {error}")
if result: print(f"Conda-build results: {result}")
#Copy the other scripts
for fname in ['install.bat', 'Run Analysis.bat']:
    shutil.copyfile(os.path.join(buildScriptDir, fname), os.path.join(outputDir, fname))