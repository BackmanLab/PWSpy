pwspy.dataTypes package
=======================
.. py:currentmodule:: pwspy.dataTypes

.. automodule:: pwspy.dataTypes


Metadata Classes
------------------
These classes provide handling of information about an acquisition without requiring that the full data be loaded into RAM. These can be used to get information
about the equipment used, the date the acquisition was taken, the location of the files, the presence of ROIs or analyses, etc.

.. autosummary::
    :nosignatures:

    ICMetaData
    DynMetaData
    ERMetaData

Data Classes
-----------------
These classes are used to actuallly load and manipulate acquisition data. The all have a corresponding metadata class.

.. autosummary::
    :nosignatures:

    ImCube
    DynCube
    KCube
    ExtraReflectanceCube
    ExtraReflectionCube

Other Classes
---------------
.. autosummary::
    :nosignatures:

    Roi
    CameraCorrection
    AcqDir
    FluorescenceImage

API
--------

.. autoclass:: ICMetaData
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: DynMetaData
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: ERMetaData
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: ImCube
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: DynCube
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: KCube
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: ExtraReflectanceCube
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: ExtraReflectionCube
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: Roi
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: FluorescenceImage
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: CameraCorrection
    :members:
    :undoc-members:
    :show-inheritance:


.. inheritance-diagram:: ImCube DynCube ICMetaData DynMetaData FluorescenceImage CameraCorrection Roi ERMetaData ExtraReflectionCube ExtraReflectanceCube KCube AcqDir FluorMetaData
    :top-classes: ICBase, ICMetaData
    :parts: 1
