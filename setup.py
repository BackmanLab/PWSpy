# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick Anthony
"""
from setuptools import setup, find_packages

setup(name='pwspy',
      version='0.0.1',
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
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
      package_data={'pwspy': ['utility/refractiveIndexFiles/*',
								'utility/thinFilmInterferenceFiles/*',
								'apps/_resources/*',
								'analysis/_resources/*',
                                'apps/PWSAnalysisApp/_resources/*',
                              'dataTypes/jsonSchemas/*']},
      packages=find_packages('src'))
