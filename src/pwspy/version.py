import logging
import os
import inspect


currDir = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename)) # Unlike __file__ this should give the correct filenme even when run from exec()
rootDir = os.path.dirname(os.path.dirname(currDir))
versionFile = os.path.join(currDir, '_version')
logger = logging.getLogger(__name__)
try:
    import git
    repo = git.Repo(rootDir)
    version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
    with open(versionFile, 'w') as f: #Overwrite the version file
        f.write(version)
    logger.info(f"Saved version, {version}, to the `_version` file.")
except Exception as e:
    # import traceback
    # traceback.print_exc()
    pass

with open(versionFile, 'r') as f:  # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
    pwspyVersion = str(f.readline())
