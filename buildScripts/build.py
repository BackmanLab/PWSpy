from git import Repo
import os
import shutil
import subprocess
"""This builds the pwpsy conda package and saves it to `build`
It should be run from the base conda env."""

buildScriptDir = os.path.dirname(os.path.abspath(__file__)) #Location of build scripts
rootDir = os.path.split(buildScriptDir)[0] #Parent directory of project.
buildDir = os.path.join(rootDir, 'build')

# Set the version number of the package. this should be shared by the package itself, the setup.py file, and the conda package `yaml`
repo = Repo(rootDir)
version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
with open(os.path.join(rootDir, 'src', 'pwspy', '_version'), 'w') as f: #Overwrite the version file
    f.write(version)
print(f"Saved version, {version}, to the `_version` file.")


#Clean
if os.path.exists(buildDir):
    shutil.rmtree(buildDir)
os.mkdir(buildDir)

# Build and save to the outputDirectory
proc = subprocess.Popen(f"conda-build {rootDir} --output-folder {buildDir} -c conda-forge", stdout=None, stderr=subprocess.PIPE)
print("Waiting for conda-build")
proc.wait()
result, error = proc.communicate() #Unfortunately conda-build returns errors in STDERR even if the build succeeds.
if proc.returncode != 0:
    raise OSError(error.decode())
else:
    print("Success")
    
#Upload to Anaconda
#The user can enable conda upload in order to automatically do this after build.
    

#Copy the other scripts
for fname in ['install Windows.bat', 'Run Analysis Windows.bat', 'Run Analysis Mac.sh', 'install Mac.sh']:
    shutil.copyfile(os.path.join(buildScriptDir, fname), os.path.join(buildDir, fname))
