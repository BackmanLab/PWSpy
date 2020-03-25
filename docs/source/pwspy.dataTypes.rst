pwspy.dataTypes package
=======================
.. py:currentmodule:: pwspy.dataTypes

.. automodule:: pwspy.dataTypes


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


.. inheritance-diagram:: ImCube DynCube ICMetaData DynMetaData FluorescenceImage CameraCorrection Roi ERMetaData ExtraReflectionCube ExtraReflectanceCube KCube AcqDir FluorMetaData
    :top-classes: ICBase, ICMetaData
    :parts: 1
