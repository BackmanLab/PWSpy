# -*- coding: utf-8 -*-
"""
Custom datatypes that are commonly used in the analysis of PWS related data.


Metadata Classes
------------------
These classes provide handling of information about an acquisition without requiring that the full data be loaded into RAM. These can be used to get information
about the equipment used, the date the acquisition was taken, the location of the files, the presence of ROIs or analyses, etc.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    ICMetaData
    DynMetaData
    ERMetaData

Data Classes
-----------------
These classes are used to actuallly load and manipulate acquisition data. The all have a corresponding metadata class.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    ImCube
    DynCube
    KCube
    ExtraReflectanceCube
    ExtraReflectionCube
    ICBase
    ICRawBase

Other Classes
---------------
.. autosummary::
    :toctree: generated/
    :nosignatures:

    Roi
    CameraCorrection
    AcqDir
    FluorescenceImage

Inheritance
-------------
.. inheritance-diagram:: ImCube DynCube ICMetaData DynMetaData FluorescenceImage CameraCorrection Roi ERMetaData ExtraReflectionCube ExtraReflectanceCube KCube AcqDir FluorMetaData
    :top-classes: ICBase, ICMetaData
    :parts: 1

"""

import os
_jsonSchemasPath = os.path.join(os.path.split(__file__)[0], 'jsonSchemas')
from ._metadata import (ICMetaData, AcqDir, DynMetaData, ERMetaData, FluorMetaData, AnalysisManagerMetaDataBase,
                        MetaDataBase)
from ._other import Roi, CameraCorrection
from ._data import (FluorescenceImage, ExtraReflectanceCube, ExtraReflectionCube, ImCube, KCube, DynCube, ICBase,
                    ICRawBase)

__all__ = ['ICMetaData', 'AcqDir', 'DynMetaData', 'ERMetaData', 'FluorMetaData', 'AnalysisManagerMetaDataBase',
           'MetaDataBase', 'Roi', 'CameraCorrection', 'FluorescenceImage', 'ExtraReflectionCube',
           'ExtraReflectanceCube', 'ImCube', 'KCube', 'DynCube', 'ICBase', 'ICRawBase']






