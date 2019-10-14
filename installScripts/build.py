from git import Repo
import os
import shutil
import subprocess
"""This builds the pwpsy conda package and saves it to `outputDir`
It should be run from the base conda env."""

outputDir = 'I:'


buildScriptDir = os.path.split(__file__)[0] #Location of build scripts
buildDir = os.path.split(buildScriptDir)[0] #Parent directory of project.

# Set the version number of the package. this should be shared by the package itself, the setup.py file, and the conda package `yaml`
versionNumber = '0.0.1'
repo = Repo(buildDir)
pwspydir = os.path.join(repo.working_tree_dir, 'src', 'pwspy')
with open(os.path.join(pwspydir, '_version'), 'w') as f: #Overwrite the version file
    f.write(versionNumber)

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