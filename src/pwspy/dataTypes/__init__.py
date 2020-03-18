# -*- coding: utf-8 -*-
"""
Data Types Module
==================
This module contains all custom datatypes that are commonly used in the analysis of PWS related data.

Metadata classes
------------------
These classes provide handling of information about an acquisition without requiring that the full data be loaded into RAM. These can be used to get information
about the equipment used, the date the acquisition was taken, the location of the files, the presence of ROIs or analyses, etc.

:class:`ICMetaData`:
    Metadata for a PWS acquisition

:class:`DynMetaData`:
    Metadata for a dynamics acquisition

:class:`ERMetadata`:
    Metadata for an extra reflectance calibration file.

TODO continue this.
"""
import os
_jsonSchemasPath = os.path.join(os.path.split(__file__)[0], 'jsonSchemas')
from ._metadata import ICMetaData, DynMetaData, ERMetadata, MetaDataBase, FluorMetaData
from ._otherClasses import Roi, CameraCorrection
from ._FluoresenceImg import FluorescenceImage
from ._arrayClasses import ImCube, DynCube, ExtraReflectionCube, ExtraReflectanceCube, KCube, ICBase, ICRawBase
from ._AcqDir import AcqDir

__all__ = ['ICBase', 'ICRawBase', 'ICMetaData', 'DynMetaData', 'ERMetadata', 'Roi', 'CameraCorrection', 'FluorescenceImage', 'ImCube', "DynCube",
           "ExtraReflectionCube", "ExtraReflectanceCube", 'KCube', 'AcqDir', 'FluorMetaData']






