# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick Anthony
"""
from setuptools import setup, find_packages
import os.path as osp
from git import Repo

# Set the version number of the package. this should be shared by the package itself, the setup.py file, and the conda package `yaml`
repo = Repo(rootDir)
version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
pwspydir = os.path.join(repo.working_tree_dir, 'src', 'pwspy')
with open(os.path.join(pwspydir, '_version'), 'w') as f: #Overwrite the version file
    f.write(version)
print(f"Saved version, {version}, to the `_version` file.")

setup(name='pwspy',
      version=version,
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      url='https://bitbucket.org/backmanlab/pwspython/src/master/'
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
                        'opencv-contrib-python'],
      package_dir={'': 'src'},
      package_data={'pwspy': ['utility/reflection/refractiveIndexFiles/*',
								'utility/thinFilmInterferenceFiles/*',
								'apps/_resources/*',
								'analysis/_resources/defaultAnalysisSettings/*',
                                'apps/PWSAnalysisApp/_resources/*',
                              'dataTypes/jsonSchemas/*',
                              '_version']},
      packages=find_packages('src'))
