PWSpy
=========

PWSpy is a Python library for working with Partial Wave Spectroscopic Microscopy data. It provides a concise and simple interface for
loading and analyzing experimental data. Support for modern as well as legacy file formats of PWS data is provided.

With PWSpy, it is trivial to skip to skip the basics and get to the heart of extracting meaningful results from your experimental data. Basic operations such as normalization, hardware compensation, and calibration are handled with the call of a single method. Additionally, the library provides a means for conveniently loading and storing auxiliary data such as ROIs, notes, and analysis outputs.

Utility functionality for generating visualizations, automatic colocalization, calculation of thin-film reflectance based on fresnel equations, parsing metadata from the graph-based acquisition engine, and more are provided in the utility subpackage.

Usage
=======

Almost any usage of PWSpy will start with loading of experimental data. The simplest way to do this is
with the :py:class:`pwspy.dataTypes.Acquisition` class. An instance of `Acquisition` provides properties (`pws`, `dynamics`,
`fluorescence`) which provide references to colocalized measurements which may be part of a single acquisition.

.. code-block::

    import pwspy.dataTypes as pwsdt

    acq = pwsdt.Acquisition(pathToData)

    pwsMetadata = acq.pws

    if acq.dynamics is not None:
        dynamicsMetadata = acq.dynamics

    if acq.fluorescence is not None:
        listOfFluorMetadata = acq.fluorescence



An acquisition also provides access to information that applies to all measurements such as ROIs and automated imaging
metadata.

.. code-block::

    roiInfos: List[Tuple[str, int, Roi.FileFormat]] = acq.getRois()
    for roiInfo in roiInfos:
        roiFile = acq.loadRoi(*roiInfo)

Each sub-measurement metadata object of an `Acquisition` provides access to information specific to that measurement such
as analysis results and raw data.

.. code-block::

    from pwspy.analysis.pws import PWSAnalysisResults
    from pwspy.analysis.dynamics import DynAnalysisResults

    listOfAnalysisNames = acq.pws.getAnalyses()
    analysisName = listOfAnalysisNames[0]

    pAnalysisResults: PWSAnalysisResults = acq.pws.loadAnalysis(analysisName)
    dAnalysisResults: DynAnalysisResults = acq.dynamics.loadAnalysis(analysisName)
    roi: pwsdt.Roi = acq.loadRoi(roiName, roiNumber).getRoi()

    print(f"Average nuclear Sigma is: {pAnalysisResults.rms[roi.mask].mean()}")
    print(f"Average nuclear Sigma_t^2 is: {dAnalysisResults.rms_t_squared[roi.mask].mean()}")

There is much more functionality in this library, please see the examples and API documentation.



API
===================

.. automodule:: pwspy

Examples
===========
.. toctree::
    examples

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
