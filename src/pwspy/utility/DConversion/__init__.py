"""This module contains an adaptation of Adam Eshein's (aeshein@u.northwestern.edu) MATLAB code for converting PWS
RMS measurements to D. The MATLAB code was based on Vadim-Backman's (v-backman@northwestern.edu) original code in
Mathematica.

REFERENCES
   L. Cherkezyan, D. Zhang, H. Subramanian, I. Capoglu, A. Taflove,
   V. Backman, "Review of interferometric spectroscopy of scattered light
   for the quantification of subdiffractional structure of biomaterials."
   J. of Biomedical Optics, 22(3), 030901 (2017).

"""

import numpy as np
from scipy.integrate import quad
# TODO see email from self (nicholas.anthony@northwestern.edu) on 3/26/2019 showing how the equations can be simplified to be more efficient)


@np.vectorize
def expn(n: float, x: float) -> float:
    """This is a custom implementation of the generalized exponential exponential integral `En`. The implementation in `scipy.special.expn` is faster but only supports
    integers for `n`.

    :math:`\\int_0^{\\infty} \\! \\frac{e^{-x*t}}{t^n} \\, \\mathrm{d}t`


    Args:
        n: The exponent of the divisor
        x: The exponent of the inverse exponential

    Returns:
        The result of the integral :math:`\\int_0^{\\infty} \\! \\frac{e^{-x*t}}{t^n} \\, \\mathrm{d}t`
    """
    def integrand(t: float, N: float, X: float):
        return np.exp(-X*t) / t**N
    return quad(integrand, 1, np.inf, args=(n, x))[0]


def _acf(d, lmin, lmax, x):
    """This function is based on the `acf_1` MATLAB function.

    Args:
        d:
        lmin:
        lmax:
        x:

    Returns:

    """
    out = ((3 - d) * ((((lmin**4) * ((lmin / lmax)**(-d)) * expn(-2 + d, x / lmax)) / (lmax**3)) - lmin * expn(-2 + d, x / lmin))) / (lmin * (1 - (lmin / lmax)**(3-d)))
    return out


def _acfd(d, lmin, lmax):
    """This function is based on the `acfd` MATLAB function.

    Args:
        d:
        lmin:
        lmax:

    Returns:

    """
    delta = 0.1
    x = (lmax+lmin) / 100
    out = 3 + (np.log(_acf(d, lmin, lmax, x + delta)) - np.log(_acf(d, lmin, lmax, x))) / (np.log(x + delta) - np.log(x))
    return out


def _calcDSize(raw_rms: np.ndarray, noise: float, NAi: float):
    """
    The `system_correction` argument from the original MATLAB function has been excluded. We assume that any RMS
    values being provided to this function have already been properly corrected for hardware defects.

    Args:
        raw_rms: An array of RMS values you wish to convert.
        noise: A positive value indicating the background noise in the system in terms of RMS (E.G. the RMS of
            a measurement of clean glass). On the Backman lab "STORM" system this has been previously
            found to be 0.012. For the "LCPWS1" system it has been found to be 0.009.
        NAi: The illumination numerical aperture (NA) of the objective.

    Returns:
        d_size: :todo:
    """
    sigma = np.real(np.sqrt(raw_rms**2 - noise**2))
    d_size = sigma * 13.8738 * NAi + 1.473
    return d_size


def sigma2D(raw_rms: np.ndarray, noise: float, NAi: float) -> np.ndarray:
    """Converts d_size to D precisely. This function can be significantly slower than
    `sigma2DApproximation` but more closely follows the analytical solution.

    Args:
        raw_rms: An array of RMS values you wish to convert.
        noise: A positive value indicating the background noise in the system in terms of RMS (E.G. the RMS of
            a measurement of clean glass). On the Backman lab "STORM" system this has been previously
            found to be 0.012. For the "LCPWS1" system it has been found to be 0.009.
        NAi: The illumination numerical aperture (NA) of the objective.

    Returns:
        d_exact: Results from the exact solution of converting from sigma to D. This calculation is based on
            derivations by Vadim Backman.
    """
    d_size = _calcDSize(raw_rms, noise, NAi)
    #This runs 6 times faster than the matlab version for some reason
    mf = 1000000
    d_size[d_size == 3] = 3.00001

    lmaxlminapprox = 100
    correction = ((3 - d_size) * (1 - (lmaxlminapprox**(-1. * d_size)))) / (
                d_size * (1 - (lmaxlminapprox**(d_size - 3))))
    mass = mf / correction
    d_exact = _acfd(d_size, 1, mass ** (1. / d_size))
    return d_exact


def sigma2DApproximation(raw_rms: np.ndarray, noise: float, NAi: float) -> np.ndarray:
    """Converts d_size to D using a 15th degree polynomial approximation of the `sigma2D` function. This function can be
    significantly faster than `sigma2D` but is not guaranteed to be accurate especially at extreme input values.

    Args:
        raw_rms: An array of RMS values you wish to convert.
        noise: A positive value indicating the background noise in the system in terms of RMS (E.G. the RMS of
            a measurement of clean glass). On the Backman lab "STORM" system this has been previously
            found to be 0.012. For the "LCPWS1" system it has been found to be 0.009.
        NAi: The illumination numerical aperture (NA) of the objective.

    Returns:
        d_estimate: This is an estimation of D calculated from Sigma. It's based on a 15th order polynomial fit of
         the output from the `sigma2D` function. No value of D yields error >0.1%.
    """
    d_size = _calcDSize(raw_rms, noise, NAi)
    # These are the polynomical coefficients stored in the SimgaToD_coefs.mat file. They go from high order to low, E.G. x^2 + x + 1
    sigmaToD_coefs = [-9.14414809736752e-09, 8.02336561707375e-07, -3.22276589702395e-05, 0.000784980326922923, -0.0129458554989855, 0.152852475387947,
                      -1.33210715342735, 8.70614624955508, -42.9149123685218, 159.111116839950, -438.829185621276, 881.674160348790, -1246.22822358504,
                      1168.11294529161, -647.810667596662, 161.021813781994]
    d_estimate = np.polynomial.polyval(sigmaToD_coefs, d_size)  # Note do not confuse this with np.polynomial.polynomial.polyval(), the ordering is different.
    d_estimate[d_size > 10] = 2.99  # The fitting doesn't work well at very high values of D_size.
    return d_estimate


if __name__ == '__main__':


    def testexpn():
        lmin = 1
        d = np.array([2.1796160, 2.9585142, 2.6632771, 1.8785352, 1.8430616])
        x = np.array([8.8774614, 2.6083560, 3.6681373, 20.619408, 23.234888])
        res = expn(-2+d, x/lmin)
        return res