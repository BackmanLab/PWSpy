# -*- coding: utf-8 -*-
"""
Load the OPD from a previously saved analysis result and plot it using a special multi-dimensional plotting widget.

@author: Nick Anthony
"""

import pwspy.dataTypes as pwsdt
from mpl_qt_viz.visualizers import PlotNd
from examples import PWSImagePath
import matplotlib.pyplot as plt

plt.ion()  # Without this we will get a crash when trying to open the PlotNd window because a Qt application loop must be running.
plt.figure()

acquisition = pwsdt.Acquisition(PWSImagePath)  # Get a reference to the top-level folder for the measurement.

roiSpecs = acquisition.getRois()  # Get a list of the (name, number, file format) of the available ROIs.
print("ROIs:\n", roiSpecs)

analysis = acquisition.pws.loadAnalysis(acquisition.pws.getAnalyses()[0])  # Load a reference to an analysis file.
kCube = analysis.reflectance  # Load the processed `reflectance` array from the analysis file.

opd, opdValues = kCube.getOpd(useHannWindow=False, indexOpdStop=50)  # Use FFT to transform the reflectance array to OPD

# Scale the opdValues to give estimated depth instead of raw OPD. Factor of 2 because light is making a round-trip.
ri = 1.37  # Estimated RI of livecell chromatin
opdValues = opdValues / (2 * ri)

plotWindow = PlotNd(opd, names=('y', 'x', 'depth'),
                    indices=(None, None, opdValues), title="Estimated Depth")
