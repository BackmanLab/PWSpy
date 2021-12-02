# Copyright 2018-2021 Nick Anthony, Backman Biophotonics Lab, Northwestern University
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

from __future__ import annotations

import typing
import collections.abc

NumberOrArray = typing.Union[typing.Sequence[float], float]


class S2DMatlabBridge:  # TODO implement the SigmaToDApprox method as well.
    """
    Opens a MATLAB process to run the Sigma2D conversion code. You must have the MATLAB engine for Python installed
    in your Python environment.

    Args:
        s2dPath: The file path to the SigmaConversion MATLAB package.
    """
    def __init__(self, s2dPath: str):
        import matlab.engine
        self._engine = matlab.engine.start_matlab()
        self._engine.addpath(s2dPath)

    def createRIDefinitionFromGladstoneDale(self, mediaRI: float, CVC: float) -> 'matlab.object':
        """
        Create an S2D.RIDefinition object from the GladstoneDale equation.

        Args:
            mediaRI: The refractive index of the media that the chromatin is immersed in.
            CVC: The CVC, also referred to as Phi. The ratio of Chromatin Volume : Total Volume, kind of like density.

        Returns:
            A S2D.RIDefinition object.
        """
        return self._engine.S2D.RIDefinition.createFromGladstoneDale(mediaRI, CVC)

    def createSystemConfiguration(self, ri_def: 'S2D.RIDefinition', na_i: float, na_c: float, center_lambda: float,
                                  oil_immersion: bool, cell_glass_interface: bool) -> 'matlab.object':
        """
        Create a system configuration object. This object contains all information about the microscope and sample refractive indices.

        Args:
            ri_def: An RI definition object
            na_i: The illumination NA of the objective.
            na_c: The collection NA of the objective.
            center_lambda: The center wavelength of illumination. This should be the center in K-space. So, the wavelength of the center wavenumber.
            oil_immersion: If True then the objective is treated as though it is immersed in RI_glass. If False it is treated as though it is immersed in RI_media.
            cell_glass_interface: If True then the cell/glass interface is treated as the reference reflection of the configuration. If False then the cell/media interface is treated as the reference reflection.
        Returns:
            A S2D.SystemConfiguration MATLAB object.
        """
        return self._engine.S2D.SystemConfiguration(ri_def, na_i, na_c, center_lambda, oil_immersion, cell_glass_interface)

    def SigmaToD_AllInputs(self, sigmaIn: NumberOrArray, system_config: 'S2D.SystemConfiguration',
                           Nf: float, thickIn: float) -> NumberOrArray:
        """
        Run the complete sigma to D conversion function.

        Args:
            sigmaIn: The sigma values you want to convert.
            system_config: The SystemConfiguration object to use.
            Nf: The genomic length of a packing domain.
            thickIn: The expected thickness of the sample.

        Returns:
            dOut: This is analogous to `D_b` in Aya's paper. The `model parameter`.
            dCorrected: This is the true `D`. This is usually what we care about.
            Nf_expected: The genomic length we expect based on D and the calculated lMax.
            lmax_corrected: Calculation of LMax from Nf and Db based on eqn. 2.
        """
        if isinstance(sigmaIn, collections.abc.Sequence):
            import matlab
            sigmaIn = matlab.double(sigmaIn)
        return self._engine.SigmaToD_AllInputs(sigmaIn, system_config, Nf, thickIn, nargout=4)

    def close(self):
        """
        Close the MATLAB engine. This may not be necessary as the engine will be automatically closed when Python shuts down.
        """
        self._engine.quit()


if __name__ == '__main__':
    s = S2DMatlabBridge(r'C:\Users\backman05\Documents\Bitbucket\SigmaToD\SigmaConversion')
    ri = s.createRIDefinitionFromGladstoneDale(1.337, .3)
    conf = s.createSystemConfiguration(ri, .52, 1.49, 585, True, True)
    out = s.SigmaToD_AllInputs([.1, .1, .2], conf, 1e6, 3)
    a = 1
