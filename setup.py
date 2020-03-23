# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick Anthony
"""
from setuptools import setup, find_packages

import src.pwspy.version as versionFile


setup(name='pwspy',
      version=versionFile.__version__,
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      url='https://bitbucket.org/backmanlab/pwspython/src/master/',
      python_requires='>3.7',
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
                        'opencv-python',
                        'PyQt5',
                        'scikit-image'],
      package_dir={'': 'src'},
      package_data={'pwspy': ['utility/reflection/refractiveIndexFiles/*',
								'utility/thinFilmInterferenceFiles/*',
								'apps/_resources/*',
								'analysis/_resources/defaultAnalysisSettings/*',
                                'apps/PWSAnalysisApp/_resources/*',
                              'dataTypes/jsonSchemas/*']},
      packages=find_packages('src'))
