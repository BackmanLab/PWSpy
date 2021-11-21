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
import setuptools_scm

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(name='pwspy',
      version=setuptools_scm.get_version(write_to="src/pwspy/version.py"),
      description='A framework for working with Partial Wave Spectroscopic microscopy files.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      url='https://github.com/BackmanLab/PWSpy',
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
                        'opencv-python', #opencv is required but naming differences between conda and pip seem to cause issues. Maybe should be commented out?
                        'scikit-image',
                        'rasterio'],
      package_dir={'': 'src'},
      package_data={'pwspy': ['utility/reflection/refractiveIndexFiles/*',
                              'utility/thinFilmInterferenceFiles/*',
                              'analysis/_resources/defaultAnalysisSettings/*',
                              'dataTypes/jsonSchemas/*']},
      packages=find_packages('src')
	)
