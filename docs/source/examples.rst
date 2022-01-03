Examples
==========

Performing FFT on the raw data to get a view of the estimated depth of cell features
--------------------------------------------------------------------------------------
.. literalinclude:: ../../examples/opdExampleScript.py
   :language: python
   :linenos:

.. image:: ../resources/opdExample.gif


Brief example of basic PWS analysis to produce Sigma, Reflectance, Ld, and other images.
-----------------------------------------------------------------------------------------
.. literalinclude:: ../../examples/runPWSAnalysis.py
   :language: python
   :linenos:


Use the `compilation` functionality to reduce analysis results to a table of values of average values within an ROI
----------------------------------------------------------------------------------------------------------------------
.. literalinclude:: ../../examples/compileResults.py
   :language: python
   :linenos:

Basic loading of ROI's to extract data from specific regions
--------------------------------------------------------------
.. literalinclude:: ../../examples/roiUsageExample.py
   :language: python
   :linenos:

Using a hand-drawn ROI to generate a reference pseudo-measurement
--------------------------------------------------------------------
.. literalinclude:: ../../examples/ROItoReference.py
   :language: python
   :linenos:

Blurring data laterally to smooth a reference image.
-------------------------------------------------------
.. literalinclude:: ../../examples/syntheticReference.py
   :language: python
   :linenos:


Measuring Sigma using only a limited range of the OPD signal.
--------------------------------------------------------------
.. literalinclude:: ../../examples/limitedOPDSigma.py
   :language: python
   :linenos:

Generating new position lists to enable colocalized measurements on multiple systems.
--------------------------------------------------------------
.. literalinclude:: ../../examples/positionTransformation.py
   :language: python
   :linenos: