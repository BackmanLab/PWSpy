# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick Anthony
"""
from setuptools import setup, find_packages
import os

pwspydir = os.path.join(os.path.split(__file__)[0], 'src', 'pwspy')


with open(os.path.join(pwspydir, '_version'), 'r') as f:
    version = f.readline()

setup(name='pwspy',
      version=version,
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      url='https://bitbucket.org/backmanlab/pwspython/src/master/',
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
