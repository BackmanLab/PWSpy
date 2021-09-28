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

"""
An adaptation of Adam Eshein's (aeshein@u.northwestern.edu) MATLAB code for converting PWS
RMS measurements to D. The MATLAB code was based on Vadim-Backman's (v-backman@northwestern.edu) original code in
Mathematica.

References:
   L. Cherkezyan, D. Zhang, H. Subramanian, I. Capoglu, A. Taflove,
   V. Backman, "Review of interferometric spectroscopy of scattered light
   for the quantification of subdiffractional structure of biomaterials."
   J. of Biomedical Optics, 22(3), 030901 (2017).

Primary Functions
-----------------
.. autosummary::
   :toctree: generated/

   sigma2D
   sigma2DApproximation

Secondary Functions
--------------------
These functions are called by the primary functions and probably don't need to be used directly.

.. autosummary::
   :toctree: generated/

   expn
   acf
   acfd
   calcDSize

Classes
-----------
This class is used to connect to the MATLAB Sigma to D conversion library.

.. autosummary::
    :toctree: generated/

    S2DMatlabBridge

"""
from ._fromLegacyAdam import sigma2D, sigma2DApproximation, expn, acf, acfd, calcDSize
from ._matlabBridge import S2DMatlabBridge

