# PWSpy
A Python module dedicated to analysis of Partial Wave Spectroscopic Microscopy data.

## Statement of need
Any analysis of raw data generated by PWS and related imaging modes requires loading image data and metadata from a large variety of file formats, performing complex pre-processing steps before any of the real analysis begins. Any minor variations in how this pre-processing is performed can result in major differences in final analysis results. PWSpy provides an object-oriented interface for performing all common file I/O and analysis tasks related to PWS. This allows users to write succinct and readable scripts/software that function identically regardless of the file format of the raw data and which are guaranteed to perform all basic operations properly. The analysis steps described in previous publications ([1](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5348632/), [2](https://www.nature.com/articles/s41467-019-09717-6), [3](https://www.osapublishing.org/ol/viewmedia.cfm?uri=ol-45-17-4810&seq=0&html=true)) can be found written out clearly in Python under the `analysis` package. Classes providing uniform file handling for the current file format used by the [PWS Acquisition plugin for Micro-Manager](https://github.com/nanthony21/PWSAcquisition) as well as all known legacy formats can be found under the `dataTypes` package.  This library provides support for the backend code of [PWSpy_GUI](https://github.com/nanthony21/pwspy_gui).

## Documentation
API documentation is hosted online at [ReadTheDocs](https://pwspy.readthedocs.io/en/dev/)

## Installation
`PWSpy` is most easily installed with the [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html) package manager.
It is advisable to install `PWSpy` into it's own Conda environment to avoid dependency conflicts. 
Create a new environment with the command: `conda create -n {environmentName} python=3.7`. You can then make the new environment active in your terminal with `conda activate {environmentName}`.

More information [here](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).

#### Installing from Anaconda Cloud (recommended)
`PWSpy` is published online to the "backmanlab" Anaconda Cloud channel. It can be installed from Conda with the command `conda install -c conda-forge -c backmanlab pwspy` 

#### Installing with Pip
`PWSpy` is available on PyPi and can be installed using Pip, however some of its dependencies may not automatically install properly. Installing via `conda` is the easiest method.

## Building from source and distributing
For information on creating a Conda package yourself see [here](docs/building.md).

## Contributing
Read the [contributing section](CONTRIBUTING.md) in the documentation if you want to help us improve and further develop PWSpy!

