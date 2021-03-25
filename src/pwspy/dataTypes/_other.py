# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick Anthony
"""
from __future__ import annotations
import json
import logging
import os
import warnings

from matplotlib import patches
import dataclasses
from enum import Enum, auto
from glob import glob
from typing import List, Tuple, Optional
import matplotlib.pyplot as plt
import h5py
import numpy as np
from scipy import io as spio
from scipy.spatial.qhull import Delaunay
from shapely import geometry
from shapely.ops import cascaded_union, polygonize
import cv2
from rasterio import features
import shapely
import typing
import copy
if typing.TYPE_CHECKING:
    from matplotlib.image import AxesImage

# TODO split into ROI and ROIFile classes.


@dataclasses.dataclass(frozen=True)
class CameraCorrection:
    """This class represents all the information needed to correct camera related hardware defects in our data. This
    includes a dark count value (The counts registered when no light is incident on the camera. It also includes a
    polynomial that is used to linearize the counts. E.G. if you image something over a range of exposure times you would
    expect the measured counts to be proportional to the exposure time. However on some cameras this is not the case.

    Attributes:
        darkCounts: Dark count for a single pixel of the camera. This will be subtracted from the data in pre-processing.
            When binning is used the dark counts are summed together, so if you measure a dark count of 400 with 2x2
            binning then the single pixel dark count is 100.
        linearityPolynomial: Sequence of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc...
            Used to linearize the counts from the camera so that they are linearly proportional to the image brightness.
            This can generally be left as `None` for sCMOS cameras but it is often required for CCD type cameras.
    """
    darkCounts: float
    linearityPolynomial: typing.Sequence[float, ...] = None

    def __post_init__(self):
        # This code runs right after the built-in dataclass initializer runs.
        # Force the linearity polynomial to be a tuple.
        if self.linearityPolynomial is not None:
            object.__setattr__(self, 'linearityPolynomial', tuple(self.linearityPolynomial))
            assert isinstance(self.linearityPolynomial, tuple)

    def toJsonFile(self, filePath: str):
        """
        Save the camera correction to a JSON formatted text file.

        Args:
            filePath: The file path for the new JSON file.
        """
        if os.path.splitext(filePath)[-1] != '.json':
            filePath = filePath + '.json'
        with open(filePath, 'w') as f:
            json.dump(dataclasses.asdict(self), f)

    @classmethod
    def fromJsonFile(cls, filePath: str) -> CameraCorrection:
        """
        Load the camera correction from a json text file.

        Args:
             filePath: The file path of the JSON file to load from.

        Returns:
            A new instance of `CameraCorrection`.

        Examples:
            corr = CameraCorrection.fromJsonFile('~/Desktop/camera.json')

        """
        with open(filePath, 'r') as f:
            return cls(**json.load(f))


class Roi:  # TODO get more in line with shapely. Remove all Matplotlib
    """This class represents a single Roi used to select a specific region of an image. The Roi consists of a `mask` (a boolean array specifying which pixels are
    included in the Roi), a set of of `vertices` (a 2 x N array specifying the vertices of the polygon enclosing the
    mask, this is useful if you want to adjust the Roi later. Rather than calling the constructor directly you will
    generally create one of these objects through one of the `class methods` that construct one for you.

    Args:
        mask: A 2D boolean array where the True values indicate pixels that are within the ROI.
        verts: Can be a sequence of 2D (x, y) coordinates indicating the border of the ROI or a shapely `Polygon`.
            If an array of coordinates is used then it will be converted to the shell of a shapely polygon internally.
            While this information is partially redundant with the mask it is useful for many applications and can be
            complicated to calculate from `mask`.
    """

    def __init__(self, mask: np.ndarray, verts: typing.Union[np.ndarray, geometry.Polygon]):
        assert isinstance(mask, np.ndarray), f"Mask data is of type: {type(mask)}. Must be numpy array."
        assert len(mask.shape) == 2
        assert mask.dtype == np.bool
        self._polygon: geometry.Polygon
        if isinstance(verts, geometry.Polygon):
            self._polygon = verts
        else:
            assert len(verts.shape) == 2
            assert verts.shape[1] == 2
            self._polygon = geometry.Polygon(shell=verts)
        self.mask = mask

    @property
    def verts(self) -> np.ndarray:
        return np.array(self._polygon.exterior.coords)

    @classmethod
    def fromVerts(cls, verts: np.ndarray, dataShape: typing.Tuple[float, float]) -> Roi:
        """
        Automatically generate the mask for an Roi using just the vertices of an enclosing polygon.

        Args:
            verts: A sequence of 2D (x, y) coordinates indicating the border of the ROI.
            dataShape: A tuple giving the shape of the array that this Roi is associated with.

        Returns:
            A new instance of `Roi`

        Examples:
            myRoi = Roi.fromVerts('nucleus', 1, polyVerts, (1024, 1024))

        """
        assert isinstance(verts, np.ndarray)
        assert isinstance(dataShape, tuple)
        assert len(dataShape) == 2
        assert verts.shape[1] == 2
        assert len(verts.shape) == 2
        iVerts = np.rint([verts]).astype(np.int32)  # The brackets here convert to a 3d array which is what cv2.fillpoly expects. We have to round to integers for cv2 to work.
        mask = np.zeros(dataShape, dtype=np.int32)
        cv2.fillPoly(mask, iVerts, 1)
        mask = mask.astype(bool)
        return cls(mask, verts)

    @classmethod
    def fromMask(cls, mask: np.ndarray) -> Roi:
        """
        Use rasterio to create find the vertices of a mask.
        Args:
            mask: A boolean array. The mask have only one contiguous `True` region

        Returns:
            A new instance of `Roi`

        TODO:
            This function doesn't work properly if there is a `False` region of `mask` completely enclosed by a `True` region of `mask`.
        """

        all_polygons = []
        for shape, value in features.shapes(mask.astype(np.uint8), mask=mask):
            all_polygons.append(shapely.geometry.shape(shape))

        poly = sorted(all_polygons, key=lambda poly: poly.area)[-1]  # Return the biggest found polygon
        verts = np.array(poly.exterior.coords.xy).T
        return cls(mask=mask, verts=verts)

    def transform(self, matrix: np.ndarray) -> Roi:
        """Return a copy of this Roi that has been transformed by an affine transform matrix like the one returned by
        opencv.estimateRigidTransform. This can be obtained using the functions in the utility.machineVision module.

        Args:
            matrix: A 2x3 numpy array representing an affine transformation.
        Returns:
            A new instance of Roi representing this Roi after transformation.
        """
        mask = cv2.warpAffine(self.mask.astype(np.uint8), matrix, self.mask.shape).astype(np.bool)
        verts = cv2.transform(self.verts[None, :, :], matrix)[0, :, :]  # For some reason this needs to be 3d for opencv to work.
        return Roi(mask=mask, verts=verts)

    def getImage(self, ax: plt.Axes, alpha: float = 0.5, value: float = 0.5, cmap='Reds', **kwargs) -> AxesImage:
        """Return a matplotlib `AxesImage` representing the `mask` of the Roi. The image will be displayed on `ax`.

        Args:
            ax: The matplotlib `Axes` to add the plot to.
            alpha: The transparency of the image
            value: A number between 0 and 1 to determine the color of the overlay.
            cmap: The Matplotlib colormap that will be used to determine color.
            kwargs: These keyword arguments will be passed to the matplotlib.imshow function.
        Returns:
             A reference to the matplotlib `AxesImage`.
        """
        assert (value >= 0) and (value <= 1)
        arr = self.mask.astype(np.uint8) * int(255 * value)
        arr = np.ma.masked_array(arr, arr == 0)
        im = ax.imshow(arr, alpha=alpha, clim=[0, 255], cmap=cmap, **kwargs)
        return im

    def getBoundingPolygon(self) -> patches.Polygon:
        """Return a matplotlib `Polygon` representing the bounding polygon of the `mask`. In the case where a `mask` was
        saved but `vertices` were not this uses the 'Concave Hull` method to estimate the vertices of the bounding
        polygon of the `mask`.

        Returns:
            A matplotlib `Polygon` representing the border of the Roi
        """
        return patches.Polygon(self.verts, facecolor=(1, 0, 0, 0.5), linewidth=1, edgecolor=(0, 1, 0, 0.9))

    def getBoundingBox(self) -> typing.Tuple[float, float, float, float]:
        """
        Returns:
            A tuple of length 4 giving the coordinates of the rectangle that encloses this ROI in the form: (top, left, bottom, right)
        """
        xCoords, yCoords = tuple(zip(*self.verts))  # Split (x,y) coords into x and then y
        return max(yCoords), min(xCoords), min(yCoords), max(xCoords)


class ROIFile:  # TODO ensure only one exists per file
    """This class represents a single Roi File used to save and load an ROI. Each Roi File is identified by a
    `name` and a `number`. The recommended file format is HDF2, in this format multiple rois of the same name but differing
    numbers can be saved in a single HDF file.

    Args:
        name: The name used to identify this ROI. Multiple ROIs can share the same name but must have unique numbers.
        number: The number used to identify this ROI. Each ROI with the same name must have a unique number.
        roi: The ROI object associated with this file.
        filePath: The path to the file that this object was loaded from.
        fileFormat: The format of the file that this object was loaded from.
    """

    class FileFormats(Enum):
        """An enumerator of the different file formats that an ROI can be saved to."""
        MAT = auto()  # The oldest file format. Each ROI was saved to its own matlab .mat file as a boolean mask.
        HDF = auto()  # This was originally the default file format of this Python software. Each ROI of the same name was saved as a dataset in an HDF file. The dataset contained the boolean mask.
        HDF2 = auto()  # This is the best file format and is the current default. Each ROI of the same name is saved as an H5PY.Group in an HDF file. Each ROI group contains a dataset for the boolean mask as well as a dataset for the XY coordinates of the enclosing polygon. This saves us from having to constantly recalculate the outline of the ROI for processing purposes.

    def __init__(self, name: str, number: int, roi: Roi, filePath: str, fileFormat: ROIFile.FileFormats):
        self._roi = roi
        self.name = name
        self.number = number
        self.filePath = filePath
        self.fformat = fileFormat

    def getRoi(self) -> Roi:
        return copy.deepcopy(self._roi)  # Rois are mutable so return a copy.

    def __repr__(self):
        return f"ROIFile({self.name}, {self.number})"

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int, ROIFile.FileFormats]]:
        """Search the `path` for valid roi files and return the detected rois as a list of tuple where each tuple
        contains the `name`, `number`, and file format for the Roi.

        Args:
            path: The path to the folder containing the Roi files.

        Returns:
            A list of tuples containing:
                name: The detected Roi name
                number: The detected Roi number
                fformat: The file format of the file that the Roi is stored in
        """
        patterns = [('BW*_*.mat', ROIFile.FileFormats.MAT), ('ROI_*.h5', ROIFile.FileFormats.HDF)]
        files = {fformat: glob(os.path.join(path, p)) for p, fformat in patterns}  # Lists of the found files keyed by file format
        ret = []
        for fformat, fileNames in files.items():
            if fformat == ROIFile.FileFormats.HDF:
                for i in fileNames:
                    with h5py.File(i, 'r') as hf:  # making sure to open this file in read mode makes the function way faster!
                        for g in hf.keys():
                            if isinstance(hf[g], h5py.Group):  # Current file format
                                if 'mask' in hf[g] and 'verts' in hf[g]:
                                    assert 'ROI_' in i
                                    name = i.split("ROI_")[-1][:-3]
                                    try:
                                        ret.append((name, int(g), ROIFile.FileFormats.HDF2))
                                    except ValueError:
                                        logging.getLogger(__name__).warning(f"File {i} contains uninterpretable dataset named {g}")
                                else:
                                    raise ValueError("File is missing datasets")
                            elif isinstance(hf[g], h5py.Dataset):  # Legacy format
                                assert 'roi_' in i
                                name = i.split('roi_')[-1][:-3]  # Old files used lower case rather than "ROI_"
                                try:
                                    ret.append((name, int(g), ROIFile.FileFormats.HDF))
                                except ValueError:
                                    logging.getLogger(__name__).warning(f"File {i} contains uninterpretable dataset named {g}")

            elif fformat == ROIFile.FileFormats.MAT:
                for i in fileNames:  # list in files
                    i = os.path.split(i)[-1]
                    if len(i.split("_")) != 2:  # Some old data has files that are not ROIs but are named almost identically, this helps us avoid bugs with them.
                        continue
                    num = int(i.split('_')[0][2:])
                    name = i.split('_')[1][:-4]
                    ret.append((name, num, ROIFile.FileFormats.MAT))
        return ret

    @staticmethod
    def deleteRoi(directory: str, name: str, number: int, fformat: Optional[ROIFile.FileFormats] = None):
        """Delete the dataset associated with the Roi object specified by `name` and `num`.

        Args:
            directory: The path to the folder containing the Roi file.
            name: The name used to identify this ROI.
            number: The number used to identify this ROI.
            fformat: The format of the file.

        Raises:
            FileNotFoundError: If the file isn't found.
        """
        assert os.path.isdir(directory)
        if fformat is ROIFile.FileFormats.MAT:
            path = os.path.join(directory, f"BW{number}_{name}.mat")
        elif fformat is ROIFile.FileFormats.HDF or fformat is ROIFile.FileFormats.HDF2:
            path = os.path.join(directory, f"ROI_{name}.h5")
        elif fformat is None:  # AutoDetect the file format
            try:
                ROIFile.deleteRoi(directory, name, number, fformat=ROIFile.FileFormats.MAT)
                return
            except FileNotFoundError:
                try:
                    ROIFile.deleteRoi(directory, name, number, fformat=ROIFile.FileFormats.HDF)
                    return
                except FileNotFoundError as e:
                    raise e
        else:
            raise Exception(f"fformat of {fformat} is not accepted")

        if not os.path.exists(path):
            raise FileNotFoundError(f"The ROI file {name},{number} and format {fformat} was not found in {directory}.")

        if fformat is ROIFile.FileFormats.HDF or fformat is ROIFile.FileFormats.HDF2:
            with h5py.File(path, 'a') as hf:
                if np.string_(str(number)) not in hf.keys():
                    raise ValueError(f"The file {path} does not contain ROI number {number}.")
                del hf[np.string_(str(number))]
                remaining = len(list(hf.keys()))
            if remaining == 0:  # If the file is empty then remove it.
                os.remove(path)
        elif fformat is ROIFile.FileFormats.MAT:
            os.remove(path)
        else:
            raise Exception("Programming error.")

    @classmethod
    def fromHDF_legacy(cls, directory: str, name: str, number: int) -> ROIFile:
        """Load an Roi from an older version of the HDF file format which did not include the vertices parameter.

        Args:
            directory: The path to the directory containing the HDF file.
            name: The name used to identify this ROI.
            number: The number used to identify this ROI.
        Raises:
            OSError: If the file was not found
        Returns:
            A new instance of Roi loaded from file
        """
        path = os.path.join(directory, f'ROI_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            return cls(name, number, Roi(mask=np.array(hf[str(number)]).astype(np.bool), verts=None), filePath=path, fileFormat=ROIFile.FileFormats.HDF)

    @classmethod
    def fromHDF(cls, directory: str, name: str, number: int) -> ROIFile:
        """Load an Roi from an HDF file.

        Args:
            directory: The path to the directory containing the HDF file.
            name: The name used to identify this ROI.
            number: The number used to identify this ROI.
        Raises:
            OSError: If the file was not found
        Returns:
            A new instance of Roi loaded from file
        Examples:
            myRoi = Roi.fromHDF('~/Desktop', 'nucleus', 1)
        """
        path = os.path.join(directory, f'ROI_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            verts = hf[str(number)]['verts']
            if verts.shape is None:
                roi = Roi.fromMask(np.array(hf[str(number)]['mask']).astype(np.bool))  # Some old files could be saved without verts. allow loading them.
            else:
                roi = Roi(np.array(hf[str(number)]['mask']).astype(np.bool), verts=np.array(verts))
            return cls(name, number, roi, filePath=path, fileFormat=ROIFile.FileFormats.HDF2)

    @classmethod
    def fromMat(cls, directory: str, name: str, number: int) -> ROIFile:
        """Load an Roi from a .mat file saved in matlab. This file format is not reccomended as it does not include the
        `vertices` parameter which is useful for visually rendering and readjusting the Roi.

        Args:
            directory: The path to the directory containing the HDF file.
            name: The name used to identify this ROI.
            number: The number used to identify this ROI.
        Returns:
            A new instance of Roi loaded from file
        """
        filePath = os.path.join(directory, f'BW{number}_{name}.mat')
        spFile = spio.loadmat(filePath)
        if 'BW' in spFile.keys():
            mask = spFile['BW'].astype(np.bool)
        elif 'mask' in spFile.keys():
            mask = spFile['mask'].astype(np.bool)
        else:
            raise KeyError(f"A `mask` was not found in the `mat` file: {filePath}")
        roi = Roi.fromMask(mask)
        return cls(name, number, roi, filePath=filePath, fileFormat=ROIFile.FileFormats.MAT)

    @classmethod
    def loadAny(cls, directory: str, name: str, number: int) -> ROIFile:
        """Attempt loading any of the known file formats.

        Args:
            directory: The path to the directory containing the HDF file.
            name: The name used to identify this ROI.
            number: The number used to identify this ROI.
        Returns:
            A new instance of Roi loaded from file
        """
        try:
            return ROIFile.fromHDF(directory, name, number)
        except:
            try:
                return ROIFile.fromHDF_legacy(directory, name, number)
            except OSError:  # For backwards compatibility purposes
                return ROIFile.fromMat(directory, name, number)

    @classmethod
    def toHDF(cls, roi: Roi, name: str, number: int, directory: str, overwrite: typing.Optional[bool] = False) -> ROIFile:
        """
        Save the Roi to an HDF file in the specified directory. The filename is automatically chosen based on the
        `name` parameter of the Roi. Multiple Roi's with the same `name` will be saved into the same file if they have
        differing `number` parameters. If `overwrite` is true then any existing dataset will be replaced, otherwise an
        error will be raised.

        Args:
            roi: The ROI to save.
            name: The name name to save as. This will be part of the file name
            number: The ROI number to save as. Multiple ROIS of the same name can be saved to the same file but the numbers must be unique
            directory: The path of the folder to save the new HDF file to. The file will be named automatically based
                on the `name` attribute of the Roi
            overwrite: If True then if an Roi with the same `number` as this Roi is found it will be overwritten.
        """
        savePath = os.path.join(directory, f'ROI_{name}.h5')
        numStr = np.string_(str(number))
        verts = roi.verts.astype(np.float32)
        mask = roi.mask.astype(np.uint8)
        with h5py.File(savePath, 'a') as hf:
            if np.string_(str(number)) in hf.keys():
                if overwrite:
                    del hf[np.string_(str(number))]
                else:
                    raise OSError(f"The Roi file {savePath} already contains a dataset {number}")
            g = hf.create_group(numStr)
            g.create_dataset(np.string_("verts"), data=verts)
            g.create_dataset(np.string_("mask"), data=mask, compression=5)
        return cls(name, number, roi, filePath=directory, fileFormat=ROIFile.FileFormats.HDF2)

    def delete(self):
        """
        Delete the dataset associated with the Roi object.

        """
        self.deleteRoi(self.filePath, self.name, self.number)
        self._roi = None  # Just to make sure we don't still try to use the deleted file.
        self.filePath = None
        self.name = None
        self.number = None

    def update(self, roi: Roi):
        """
        Save a new roi to the existing file.
        Args:
            roi: The updated ROI to save
        """
        if self.fformat is not ROIFile.FileFormats.HDF2:
            raise NotImplementedError(f"ROIFile of format: {self.fformat} cannot be updated.")
        self.toHDF(roi, self.name, self.number, self.filePath, overwrite=True)
        self._roi = copy.deepcopy(roi)  # We don't wont to use the same object that might still have external mutable references