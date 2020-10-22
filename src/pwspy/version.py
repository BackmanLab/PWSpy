# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

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
    pass

with open(versionFile, 'r') as f:  # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
    pwspyVersion = str(f.readline())
