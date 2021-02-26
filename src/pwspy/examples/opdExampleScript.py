# -*- coding: utf-8 -*-
"""
Load the OPD from a previosly saved analysis result and plot it using a special multi-dimensional plotting widget.

@author: Nick Anthony
"""
if __name__ == '__main__':

    import pwspy.dataTypes as pwsdt
    from mpl_qt_viz.visualizers import PlotNd

    imageDirectory = r'\\backmanlabnas.myqnapcloud.com\home\Year3\ethanolTimeSeries\LTL20l_Pure\Track_3hrs\Cell3'

    acquisition = pwsdt.AcqDir(imageDirectory)

    roiSpecs = acquisition.getRois()
    print("ROIs:\n", roiSpecs)

    imCube = acquisition.pws.toDataClass()
    kCube = pwsdt.KCube.fromImCube(imCube)
    del imCube

    opd, opdValues = kCube.getOpd(isHannWindow = False, indexOpdStop = 50)

    ri = 1.37
    opdValues = opdValues / (2 * ri)

    plotWindow = PlotNd(opd, names=('y', 'x', 'depth'),
                        indices=(None, None, opdValues), title="Estimated Depth")