# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick Anthony
"""
from setuptools import setup, find_packages
import os.path as osp
import os

with open(osp.join('src', 'pwspy', 'version.py')) as f:
    currwd = os.getcwd()
    os.chdir(osp.join(currwd, 'src','pwspy')) #The version.py file will run from the wrong location if we don't manually set it here.
    exec(f.read()) # Run version py to initialize pwspyVersion
    os.chdir(currwd)

setup(name='pwspy',
      version=pwspyVersion,
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
      entry_points={'gui_scripts': [ # Not sure what effect this has if any.
          'PWSAnalysis = pwspy.apps.__main__:main',
          "ERCreator = pwspy.apps.__main__:main"
      ]},
      package_dir={'': 'src'},
      package_data={'pwspy': ['utility/reflection/refractiveIndexFiles/*',
								'utility/thinFilmInterferenceFiles/*',
								'apps/_resources/*',
								'analysis/_resources/defaultAnalysisSettings/*',
                                'apps/PWSAnalysisApp/_resources/*',
                              'dataTypes/jsonSchemas/*']},
      packages=find_packages('src'))
