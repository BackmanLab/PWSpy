import pytest
import shapely.geometry
import numpy as np
import pwspy.dataTypes as pwsdt


def test_roi(sequenceData):
    """Test that ROIs can be detected, loaded, and that the various required attributes have the expected data types."""
    acqs = [pwsdt.Acquisition(i) for i in sequenceData.datasetPath.glob("Cell[0-9]")]
    for acq in acqs:
        roiSpecs = acq.getRois()
        for roiSpec in roiSpecs:
            roiFile = acq.loadRoi(*roiSpec)
            assert roiFile.acquisition is acq
            roi = roiFile.getRoi()
            assert isinstance(roi.polygon, shapely.geometry.Polygon)
            assert isinstance(roi.verts, np.ndarray)
            assert len(roi.verts.shape) == 2
            assert roi.verts.shape[1] == 2
