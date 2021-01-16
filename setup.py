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

# -*- coding: utf-8 -*-
"""
This file is used to install the pwspy package. for example navigate in your terminal to the directory containing this
file and type `pip install .`. This file is also used by the Conda recipe (buildscripts/conda)
"""
from setuptools import setup, find_packages
import os.path as osp
import os

with open(osp.join('src', 'pwspy', 'version.py')) as f:
    currwd = os.getcwd()
    os.chdir(osp.join(currwd, 'src','pwspy')) #The version.py file will run from the wrong location if we don't manually set it here.
    exec(f.read()) # Run version py to initialize the pwspyVersion variable
    os.chdir(currwd)

setup(name='pwspy',
      version=pwspyVersion,
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      url='https://bitbucket.org/backmanlab/pwspython/src/master/',
      python_requires='>=3.7',
      install_requires=['numpy',
                        'scipy',
                        'matplotlib',
                        'tifffile',
                        'psutil',
                        'shapely',
                        'pandas',
                        'h5py',
                        'jsonschema',
                        'google-api-python-client',
                        'google-auth-httplib2',
                        'google-auth-oauthlib',
                        'opencv-python', #opencv is required but naming differences between conda and pip seem to cause issues. Maybe should be commented out?
                        'PyQt5',
                        'scikit-image'],
      package_dir={'': 'src'},
      package_data={'pwspy': ['utility/reflection/refractiveIndexFiles/*',
                              'utility/thinFilmInterferenceFiles/*',
                              'apps/_resources/*',
                              'analysis/_resources/defaultAnalysisSettings/*',
                              'apps/PWSAnalysisApp/_resources/*',
                              'dataTypes/jsonSchemas/*',
                              '_version']},
      packages=find_packages('src'),
	  entry_points={'gui_scripts': [
          'PWSAnalysis = pwspy.apps.PWSAnalysisApp.__main__:main',
          "ERCreator = pwspy.apps.ExtraReflectanceCreator.__main__:main"
      ]}
	)
