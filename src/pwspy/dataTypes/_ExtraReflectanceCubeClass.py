from __future__ import annotations
import json
from datetime import datetime
from typing import Tuple, Union

import h5py
import jsonschema

from pwspy.dataTypes._ICBaseClass import ICBase
import numpy as np
import os
from pwspy.moduleConsts import dateTimeFormat
import typing
import pandas as pd
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ImCube

class ERMetadata:
    """A class representing the extra information related to an ExtraReflectanceCube file. This can be useful as a object
     to keep track of a ExtraReflectanceCube without having to have the data from the file loaded into memory."""
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'time', 'wavelengths', 'pixelSizeUm', 'binning', 'numericalAperture'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'wavelengths': {'type': 'array',
                                        'items': {'type': 'number'}
                                        },
                       'pixelSizeUm': {'type': ['number', 'null']},
                       'binning': {'type': ['integer', 'null']},
                       'numericalAperture': {'type': ['number']}
                        }
                   }
    FILESUFFIX = '_eReflectance.h5'
    DATASETTAG = 'extraReflection'
    MDTAG = 'metadata'

    def __init__(self, inheritedMetadata: dict, numericalAperture: float, filePath: str=None):
        """The metadata dictionary will often just be inherited information from one of the ImCubes that was used to create
        this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
        an `exposure` field. In reality this ER Cube will have been created from ImCubes at a variety of exposures."""
        self.inheritedMetadata = inheritedMetadata
        self.inheritedMetadata['numericalAperture'] = numericalAperture
        jsonschema.validate(instance=inheritedMetadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self.filePath = filePath

    @property
    def idTag(self):
        return f"ExtraReflection_{self.inheritedMetadata['system']}_{self.inheritedMetadata['time']}"

    @property
    def numericalAperture(self):
        return self.inheritedMetadata['numericalAperture']

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls.FILESUFFIX in path:
            directory, name = cls.directory2dirName(path)
            with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}'), 'r') as hf:
                valid = cls.MDTAG in hf[cls.DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''

    @classmethod
    def fromHdfFile(cls, directory: str, name: str):
        filePath = cls.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[cls.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        mdDict = json.loads(d.attrs[cls.MDTAG])
        return cls(mdDict, mdDict['numericalAperture'], filePath=filePath)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        g[self.DATASETTAG].attrs[self.MDTAG] = np.string_(json.dumps(self.inheritedMetadata))
        return g

    @classmethod
    def directory2dirName(cls, path: str) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        directory, fileName = os.path.split(path)
        name = fileName.split(cls.FILESUFFIX)[0]
        return directory, name

    @classmethod
    def dirName2Directory(cls, directory: str, name: str):
        return os.path.join(directory, f'{name}{cls.FILESUFFIX}')

class ExtraReflectanceCube(ICBase):
    """This class represents a 3D data cube of the extra reflectance in a PWS system. It's values are in units of
    reflectance (between 0 and 1). It has a `metadata` attribute which is of ERMetadata. It also has a `data` attribute
    of numpy.ndarray type."""

    ERMetadata = ERMetadata

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: ERMetadata):
        assert isinstance(metadata, ERMetadata)
        if data.max() > 1 or data.min() < 0:
            print("Warning!: Reflectance values must be between 0 and 1")
        self.metadata = metadata
        ICBase.__init__(self, data, wavelengths)

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        """The wavelengths corresponding to each element along the 3rd axis of `self.data`."""
        return self.index

    @classmethod
    def fromHdfFile(cls, directory: str, name: str) -> ExtraReflectanceCube:
        """Load an ExtraReflectanceCube from an HDF5 file. `name` should be the file name, excluding the '_ExtraReflectance.h5' suffix."""
        filePath = ERMetadata.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[ERMetadata.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    def toHdfFile(self, directory: str, name: str) -> None:
        """Save an ExtraReflectanceCube to an HDF5 file. The filename will be `name` with the '_ExtraReflectance.h5' suffix."""
        savePath = os.path.join(directory, f'{name}{ERMetadata.FILESUFFIX}')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        """Save the ExtraReflectanceCube to an HDF5 dataset. `g` should be an h5py Group or File."""
        g = super().toHdfDataset(g, ERMetadata.DATASETTAG)
        g = self.metadata.toHdfDataset(g)
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        """Load the ExtraReflectanceCube from `d`, an HDF5 dataset."""
        data, index = cls._decodeHdf(d)
        md = ERMetadata.fromHdfDataset(d, filePath=filePath)
        return cls(data, index, md)

    @classmethod
    def fromMetadata(cls, md: ERMetadata):
        """Load an ExtraReflectanceCube from an ERMetadata object corresponding to an HDF5 file."""
        directory, name = ERMetadata.directory2dirName(md.filePath)
        return cls.fromHdfFile(directory, name)


class ExtraReflectionCube(ICBase):
    """This class is meant to be constructed from an ExtraReflectanceCube along with additional reference measurement
    information. Rather than being in units of reflectance (between 0 and 1) it is in the same units as the reference measurement
    that is provided with, usually counts/ms or just counts."""
    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: ERMetadata):
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @classmethod
    def create(cls, reflectance: ExtraReflectanceCube, theoryR: pd.Series, reference: ImCube):
        """Construct and ExtraReflectionCube from an ExtraReflectanceCube and a reference measurement. The resulting
        ExtraReflectionCube will be in the same units as `reference`. `theoryR` should be a spectrum describing the theoretically
        expected reflectance of the reference data cube. Both `theoryR` and `reflectance` should be in units of reflectance
        (between 0 and 1)."""
        I0 = reference.data / (theoryR[None, None, :] + reflectance.data) # I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
        data = reflectance.data * I0  # converting extraReflectance to the extra reflection in units of counts
        return cls(data, reflectance.wavelengths, reflectance.metadata)
