from git import Repo
import os
import shutil
import subprocess
import argparse
"""This builds the pwpsy conda package and saves it to `outputDir`
It should be run from the base conda env."""

parser = argparse.ArgumentParser(description="Build `pwspy` as a conda package and save it to a specified directory along with some useful installation scripts.")
parser.add_argument("outputDirectory", type=str, help="The directory that the built conda package should be saved to.")
args = parser.parse_args()
outputDir = args.outputDirectory
print(outputDir)
assert os.path.isdir(outputDir), f"Error: The directory, {outputDir}, does not exist."

buildScriptDir = os.path.dirname(os.path.abspath(__file__)) #Location of build scripts
buildDir = os.path.split(buildScriptDir)[0] #Parent directory of project.

# Set the version number of the package. this should be shared by the package itself, the setup.py file, and the conda package `yaml`
repo = Repo(buildDir)
version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
pwspydir = os.path.join(repo.working_tree_dir, 'src', 'pwspy')
with open(os.path.join(pwspydir, '_version'), 'w') as f: #Overwrite the version file
    f.write(version)
print(f"Saved version, {version}, to the `_version` file.")

# Build and save to the outputDirectory
proc = subprocess.Popen(f"conda-build {buildDir} --output-folder {outputDir}", stdin=None, stderr=None)
print("Waiting for conda-build")
proc.wait()
result, error = proc.communicate()

#Copy the other scripts
for fname in ['install.bat', 'Run Analysis.bat']:
    shutil.copyfile(os.path.join(buildScriptDir, fname), os.path.join(outputDir, fname))
