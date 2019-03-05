# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 20:14:25 2019

@author: Nick
"""
from setuptools import setup, find_packages

setup(name='pwspy',
      version='0.0.1',
      description='A framework for working with Partial Wave Spectroscopy files.',
      author='Nick Anthony',
      author_email='nicholas.anthony@northwestern.edu',
      license='MIT',
      install_requires=['numpy', 'scipy', 'matplotlib', 'tifffile', 'psutil', 'shapely', 'pandas', 'h5py'],
      package_dir={'': 'src'},
      package_data={'': ['*.csv', '*.png', '*.svg']},
      packages=find_packages('src'))
