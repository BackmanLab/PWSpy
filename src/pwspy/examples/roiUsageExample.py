# -*- coding: utf-8 -*-
"""
Loop through all ROIs for all acquisitions in a directory and plot a histogram of the RMS values within the ROI.

@author: Nick Anthony
"""

if __name__ == '__main__':

    import pwspy.dataTypes as pwsdt
    import matplotlib.pyplot as plt
    import pathlib
    import numpy as np
    from pwspy.examples import PWSExperimentPath
    plt.ion()

    workingDirectory = PWSExperimentPath  # The folder that all your acquisitions are saved under.
    analysisName = 'script'  # This will often be "p0"

    def plotHist(roi, rms):
        """
        This function takes an ROI
        and a 2D RMS image and plots a histogram of the RMS values inside the ROI
        """
        # Check input values just to be safe.
        assert isinstance(roi, pwsdt.Roi)  # Make sure roiFile variable is actually an ROI
        assert isinstance(rms, np.ndarray)  # Make sure the RMS image is an numpy array
        assert roi.mask.shape == rms.shape  # Make sure the ROI and RMS arrays have the same dimensions.

        vals = rms[roi.mask]  # A 1D array of the values inside the ROI
        plt.hist(vals)  # Plot a histogram


    cellFolderIterator = pathlib.Path(workingDirectory).glob("Cell[0-9]")  # An iterator for all folders that are below workingDirectory and match the "regex" pattern "Cell[0-9]"
    for folder in cellFolderIterator:
        acq = pwsdt.Acquisition(folder)  # An object handling the contents of a single "Cell{X}" folder

        try:
            anls = acq.pws.loadAnalysis(analysisName)  # Load the analysis results from file.
        except:
            print(f"Analysis loading failed for {acq.filePath}")
            continue  # Skip to the next loop iteration

        roiSpecs = acq.getRois()  # A list of the names, numbers, and fileFormats of the ROIs in this acquisition

        for name, number, fformat in roiSpecs:  # Loop through every ROI.
            roiFile = acq.loadRoi(name, number, fformat)  # Load the ROI from file.
            plotHist(roiFile.getRoi(), anls.rms)  # Use the function defined above to plot a histogram

