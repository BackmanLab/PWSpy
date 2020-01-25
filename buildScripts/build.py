from git import Repo
import os
import shutil
import subprocess
"""This builds the pwpsy conda package and saves it to `outputDir`
It should be run from the base conda env."""

buildScriptDir = os.path.dirname(os.path.abspath(__file__)) #Location of build scripts
rootDir = os.path.split(buildScriptDir)[0] #Parent directory of project.
buildDir = os.path.join(rootDir, 'build')

#Clean
shutil.rmtree(buildDir)
os.mkdir(buildDir)

# Build and save to the outputDirectory
proc = subprocess.Popen(f"conda-build {rootDir} --output-folder {buildDir} -c conda-forge", stdin=None, stderr=None)
print("Waiting for conda-build")
proc.wait()
result, error = proc.communicate()

#Upload to Anaconda
TODO

#Copy the other scripts
for fname in ['install Windows.bat', 'Run Analysis Windows.bat', 'Run Analysis Mac.sh', 'install Mac.sh']:
    shutil.copyfile(os.path.join(buildScriptDir, fname), os.path.join(buildDir, fname))
