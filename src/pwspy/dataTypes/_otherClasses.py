# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick Anthony
"""
from __future__ import annotations
import json
import os
import re
from matplotlib import patches, path
import typing
import dataclasses
from enum import Enum, auto
from glob import glob
from typing import List, Tuple
import matplotlib.pyplot as plt
import h5py
import numpy as np
from scipy import io as spio
from scipy.spatial.qhull import Delaunay
from shapely import geometry
from shapely.ops import cascaded_union, polygonize
import cv2
import typing
if typing.TYPE_CHECKING:
    from matplotlib.image import AxesImage


@dataclasses.dataclass(frozen=True)
class CameraCorrection:
    """This class represents all the information needed to correct camera related hardware defects in our data. This
    includes a dark count value (The counts registered when no light is incident on the camera. It also includes a
    polynomial that is used to linearize the counts. E.G. if you image something over a range of exposure times you would
    expect the measured counts to be proportional to the exposure time. However on some cameras this is not the case.
    linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc...
    darkCounts should be the dark count for a single pixel. When binning is used the dark counts are summed together, so
    if you measure a dark count of 400 with 2x2 binning then the single pixel dark count is 100."""
    darkCounts: float
    linearityPolynomial: typing.Tuple[float, ...] = None
    def __post_init__(self):
        # This code runs right after the built-in dataclass initializer runs.
        # Force the linearity polynomial to be a tuple.
        if self.linearityPolynomial is not None:
            object.__setattr__(self, 'linearityPolynomial', tuple(self.linearityPolynomial))
            assert isinstance(self.linearityPolynomial, tuple)

    def toJsonFile(self, filePath):
        """Save the camera correction to a json text file."""
        if os.path.splitext(filePath)[-1] != '.json':
            filePath = filePath + '.json'
        with open(filePath, 'w') as f:
            json.dump(dataclasses.asdict(self), f)

    @classmethod
    def fromJsonFile(cls, filePath):
        """Load the camera correction from a json text file.
        e.g corr = CameraCorrection.fromJsonFile('~/Desktop/camera.json')"""
        with open(filePath, 'r') as f:
            return cls(**json.load(f))


def _concaveHull(coords: List[Tuple[int, int]], alpha):
    """
    Found here: https://gist.github.com/dwyerk/10561690
    Compute the alpha shape (concave hull) of a set
    of points.
    @param coords: nx2 array of points.
    @param alpha: alpha value to influence the
        gooeyness of the border. Smaller numbers
        don't fall inward as much as larger numbers.
        Too large, and you lose everything!
    """
    if len(coords) < 4:
        # When you have a triangle, there is no sense
        # in computing an alpha shape.
        return geometry.MultiPoint(coords).convex_hull
    coords = np.array(coords)
    tri = Delaunay(coords)
    triangles = coords[tri.simplices]
    # Lengths of sides of triangle

    a = ((triangles[:, 0, 0] - triangles[:, 1, 0]) ** 2 + (triangles[:, 0, 1] - triangles[:, 1, 1]) ** 2) ** 0.5
    b = ((triangles[:, 1, 0] - triangles[:, 2, 0]) ** 2 + (triangles[:, 1, 1] - triangles[:, 2, 1]) ** 2) ** 0.5
    c = ((triangles[:, 2, 0] - triangles[:, 0, 0]) ** 2 + (triangles[:, 2, 1] - triangles[:, 0, 1]) ** 2) ** 0.5
    s = (a + b + c) / 2.0        # Semiperimeter of triangle

    areas = (s * (s - a) * (s - b) * (s - c)) ** 0.5        # Area of triangle by Heron's formula

    circums = a * b * c / (4.0 * areas)
    filtered = triangles[circums < alpha]         # Here's the radius filter.

    edge1 = filtered[:, (0, 1)]
    edge2 = filtered[:, (1, 2)]
    edge3 = filtered[:, (2, 0)]
    edge_points = np.unique(np.concatenate((edge1, edge2, edge3)), axis=0).tolist()
    m = geometry.MultiLineString(edge_points)
    triangles = list(polygonize(m))
    return cascaded_union(triangles), edge_points



class Roi:
    """This class represents a single Roi used to select a specific region of an image. Each Roi is identified by a
    `name` and a `number`. The recommended file format is HDF2, in this format multiple rois of the same name but differing
    numbers can be saved in a single HDF file. The Roi consists of a `mask` (a boolean array specifying which pixels are
    included in the Roi), a set of of `vertices` (a 2 x N array specifying the vertices of the polygon enclosing the
    mask, this is useful if you want to adjust the Roi later."""

    class FileFormats(Enum):
        """An enumerator of the different file formats that an ROI can be saved to."""
        HDF = auto()
        MAT = auto()
        HDF2 = auto()

    def __init__(self, name: str, number: int, mask: np.ndarray, verts: np.ndarray, filePath: str = None, fileFormat: Roi.FileFormats = None):
        assert isinstance(mask, np.ndarray), f"data is a {type(mask)}"
        assert mask.dtype == np.bool
        self.verts = verts
        self.name = name
        self.number = number
        self.mask = mask
        self.filePath = filePath
        self.fileFormat = fileFormat

    @classmethod
    def fromVerts(cls, name: str, number: int, verts: np.ndarray, dataShape: tuple):
        """Automatically generate the mask for an Roi using just the vertices of an enclosing polygon and the
        `dataShape` (dimensions of the full image).
        For example: myRoi = Roi.fromVerts('nucleus', 1, polyVerts, (1024, 1024))"""
        assert isinstance(verts, np.ndarray)
        assert isinstance(dataShape, tuple)
        assert len(dataShape) == 2
        assert verts.shape[1] == 2
        assert len(verts.shape) == 2
        x = np.arange(dataShape[1])
        y = np.arange(dataShape[0])
        X, Y = np.meshgrid(x, y)
        coords = list(zip(X.flatten(), Y.flatten()))
        matches = path.Path(verts).contains_points(coords)
        mask = matches.reshape(dataShape)
        return cls(name, number, mask, verts)

    @classmethod
    def fromHDF_legacy(cls, directory: str, name: str, number: int):
        """Load an Roi from an older version of the HDF file format which did not include the vertices parameter."""
        path = os.path.join(directory, f'ROI_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            return cls(name, number, mask=np.array(hf[str(number)]).astype(np.bool), verts=None, filePath=path, fileFormat=Roi.FileFormats.HDF)

    @classmethod
    def fromHDF(cls, directory: str, name: str, number: int):
        """Load an Roi from an HDF file. E.G. myRoi = Roi.fromHDF('~/Desktop', 'nucleus', 1)"""
        path = os.path.join(directory, f'ROI_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            verts = hf[str(number)]['verts']
            verts = None if verts.shape is None else np.array(verts)
            return cls(name, number, mask=np.array(hf[str(number)]['mask']).astype(np.bool), verts=verts, filePath=path,
                       fileFormat=Roi.FileFormats.HDF2)

    @classmethod
    def fromMat(cls, directory: str, name: str, number: int):
        """Load an Roi from a .mat file saved in matlab. This file format is not reccomended as it does not include the
        `vertices` parameter which is useful for visually rendering and readjusting the Roi."""
        filePath = os.path.join(directory, f'BW{number}_{name}.mat')
        return cls(name, number, mask=spio.loadmat(filePath)['BW'].astype(np.bool), verts=None, filePath=filePath, fileFormat=Roi.FileFormats.MAT)

    @classmethod
    def loadAny(cls, directory: str, name: str, number: int):
        """Attempt loading any of the known file formats."""
        try:
            return Roi.fromHDF(directory, name, number)
        except:
            try:
                return Roi.fromHDF_legacy(directory, name, number)
            except OSError: #For backwards compatibility purposes
                return Roi.fromMat(directory, name, number)

    def toHDF(self, directory: str, overwrite: bool = False):
        """Save the Roi to an HDF file in the specified directory. The filename is automatically chosen based on the
        `name` parameter of the Roi. Multiple Roi's with the same `name` will be saved into the same file if they have
        differing `number` parameters. If `overwrite` is true then any existing dataset will be replaced, otherwise an
        error will be raised."""
        savePath = os.path.join(directory, f'ROI_{self.name}.h5')
        with h5py.File(savePath, 'a') as hf:
            if np.string_(str(self.number)) in hf.keys():
                if overwrite:
                    del hf[np.string_(str(self.number))]
                else:
                    raise OSError(f"The Roi file {savePath} already contains a dataset {self.number}")
            g = hf.create_group(np.string_(str(self.number)))
            if self.verts is None:
                raise ValueError("An Roi cannot be saved to HDF without a `verts` property specifying the vertices of the"
                                 "rois enclosing polygon. You can use `getBoundingPolygon` to use Concave Hull method to generate the vertices.")
            else:
                g.create_dataset(np.string_("verts"), data=self.verts.astype(np.float32))
            g.create_dataset(np.string_("mask"), data=self.mask.astype(np.uint8), compression=5)
        self.filePath = savePath
        self.fileFormat = Roi.FileFormats.HDF2

    @staticmethod
    def deleteRoi(directory: str, name: str, num: int):
        """Only supports HDF files. Delete the dataset associated with the Roi object specified by `name` and `num`."""
        path = os.path.join(directory, f"ROI_{name}.h5")
        if not os.path.exists(path):
            raise OSError(f"The file {path} does not exist.")
        with h5py.File(path, 'a') as hf:
            if np.string_(str(num)) not in hf.keys():
                raise ValueError(f"The file {path} does not contain ROI number {num}.")
            del hf[np.string_(str(num))]
            remaining = len(list(hf.keys()))
        if remaining == 0: #  If the file is empty then remove it.
            os.remove(path)

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int, Roi.FileFormats]]:
        """Search the `path` for valid roi files and return the detected rois as a list of tuple where each tuple
        contains the `name`, `number`, and file format for the Roi."""
        patterns = [('BW*_*.mat', Roi.FileFormats.MAT), ('ROI_*.h5', Roi.FileFormats.HDF)]
        files = {fformat: glob(os.path.join(path, p)) for p, fformat in patterns} #Lists of the found files keyed by file format
        ret = []
        for fformat, fileNames in files.items():
            if fformat == Roi.FileFormats.HDF:
                for i in fileNames:
                    with h5py.File(i, 'r') as hf: # making sure to open this file in read mode make the function way faster!
                        for g in hf.keys():
                            if isinstance(hf[g], h5py.Group): #Current file format
                                if 'mask' in hf[g] and 'verts' in hf[g]:
                                    name = i.split("ROI_")[-1][:-3]
                                    try:
                                        ret.append((name, int(g), Roi.FileFormats.HDF2))
                                    except ValueError:
                                        print(f"Warning: File {i} contains uninterpretable dataset named {g}")
                                else:
                                    raise ValueError("File is missing datasets")
                            elif isinstance(hf[g], h5py.Dataset): #Legacy format
                                name = i.split('ROI_')[-1][:-3]
                                try:
                                    ret.append((name, int(g), Roi.FileFormats.HDF))
                                except ValueError:
                                    print(f"Warning: File {i} contains uninterpretable dataset named {g}")

            elif fformat == Roi.FileFormats.MAT:
                for i in fileNames: #list in files
                    i = os.path.split(i)[-1]
                    if len(i.split("_")) != 2:  # Some old data has files that are not ROIs but are named almost identically, this helps us avoid bugs with them.
                        continue
                    num = int(i.split('_')[0][2:])
                    name = i.split('_')[1][:-4]
                    ret.append((name, num, Roi.FileFormats.MAT))
        return ret

    def transform(self, matrix: np.ndarray) -> Roi:
        """return a copy of this Roi that has been transformed by an affine transform matrix like the one returned by
        opencv.estimateRigidTransform. This can be obtained using ICBase's getTransform method."""
        mask = cv2.warpAffine(self.mask.astype(np.uint8), matrix, self.mask.shape).astype(np.bool)
        if self.verts is not None: verts = cv2.transform(self.verts, matrix)
        else: verts = None
        return Roi(self.name, self.number, mask=mask, verts=verts) #intentionally ditching the filepath and fileformat data here since the new roi is not associated with a saved file.

    def getImage(self, ax: plt.Axes) -> AxesImage:
        """Return a matplotlib `AxesImage` representing the `mask` of the Roi. The image will be displayed on `ax`."""
        arr = self.mask.astype(np.uint8)*255
        arr = np.ma.masked_array(arr, arr == 0)
        im = ax.imshow(arr, alpha=0.5, clim=[0, 400], cmap='Reds')
        return im

    def getBoundingPolygon(self) -> patches.Polygon:
        """Return a matplotlib `Polygon` representing the bounding polygon of the `mask`. In the case where a `mask` was
        saved but `vertices` were not. This uses the 'Convex Hull` method to estimate the vertices of the bounding
        polygon of the `mask`."""
        if self.verts is None:  # calculate convex hull
            x = np.arange(self.mask.shape[1])
            y = np.arange(self.mask.shape[0])
            X, Y = np.meshgrid(x, y)  # Generate arrays indicating X and Y coordinates for each array element.
            X = X[self.mask]
            Y = Y[self.mask]
            coords = list(zip(X, Y))  # Get coordinates of items in the mask.
            cHull, edgePoints = _concaveHull(coords, 4)
            return patches.Polygon(cHull.exterior.coords, facecolor=(1, 0, 0, 0.5), linewidth=1, edgecolor=(0,1,0,.9))
        else:
            return patches.Polygon(self.verts, facecolor=(1, 0, 0, 0.5), linewidth=1, edgecolor=(0,1,0,0.9))


