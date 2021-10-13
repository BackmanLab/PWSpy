import numpy as np
import typing
from scipy.integrate import quad


NumberOrArray = typing.Union[np.ndarray, float]

@np.vectorize
def expn(n: float, x: float) -> float:
    """
    This is a custom implementation of the generalized exponential exponential integral. The implementation in `scipy.special.expn` is faster but only supports
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


def acf(d: NumberOrArray, lmin: NumberOrArray, lmax: NumberOrArray, x: NumberOrArray) -> NumberOrArray:
    """This function is based on the `acf_1` MATLAB function. This is how we model the ACF of the chromatin density.

    Args:
        d: :todo:
        lmin: :todo:
        lmax: :todo:
        x: :todo:

    Returns:

    """
    out = ((3 - d) * ((((lmin**4) * ((lmin / lmax)**(-d)) * expn(-2 + d, x / lmax)) / (lmax**3)) - lmin * expn(-2 + d, x / lmin))) / (lmin * (1 - (lmin / lmax)**(3-d)))
    return out


def acfd(d: NumberOrArray, lmin: NumberOrArray, lmax: NumberOrArray) -> NumberOrArray:
    """This function is based on the `acfd` MATLAB function. The equation has been algebraically refactored from the
    MATLAB code to require fewer computations of logarithms. Converts from `D_b` (the model parameter) to true `D`.

    Args:
        d: `D_b`. The model parameter of the ACF function.
        lmin: The minimum length scale over which we expect chromatin to exhibit fractal behavior.
        lmax: The maximum length scale over which we expect chromatin to exhibit fractal behavior.

    Returns:
        The true `D` value associated with the `D_b` input values.
    """
    delta = 0.1
    x = (lmax+lmin) / 100
    out = 3 + np.log(acf(d, lmin, lmax, x + delta) / acf(d, lmin, lmax, x)) / np.log((x + delta) / x)
    return out


def calcDSize(raw_rms: np.ndarray, noise: float, NAi: float):
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
        d_size: D_b from aya's paper. The "Model Parameter". Not the same as D, but related.
    """
    sigma = np.sqrt(raw_rms**2 - noise**2)  # The MATLAB version will return complex numbers if this is negative. This implementation returns `nan`
    d_size = sigma * 13.8738 * NAi + 1.473
    return d_size


def sigma2D(raw_rms: np.ndarray, noise: float, NAi: float) -> np.ndarray:
    """
    Converts d_size to D precisely. This function can be significantly slower than
    `sigma2DApproximation` but more closely follows the analytical solution.

    Args:
        raw_rms: An array of RMS values you wish to convert.
        noise: A positive value indicating the background noise in the system in terms of RMS (E.G. the RMS of
            a measurement of clean glass). On the Backman lab "STORM" system this has been previously
            found to be 0.012. For the "LCPWS1" system it has been found to be 0.009.
        NAi: The illumination numerical aperture (NA) of the objective.

    Returns:
        Results from the exact solution of converting from Sigma to D. This calculation is based on
        derivations by Vadim Backman.
    """
    d_size = calcDSize(raw_rms, noise, NAi)
    #This runs 6 times faster than the matlab version for some reason
    mf = 1000000
    d_size[d_size == 3] = 3.00001  # d_size == 3 will result in a singularity so we nudge the data a bit.

    lmaxlminapprox = 100
    correction = ((3 - d_size) * (1 - (lmaxlminapprox**(-1. * d_size)))) / (
                d_size * (1 - (lmaxlminapprox**(d_size - 3))))
    mass = mf / correction
    d_exact = acfd(d_size, 1, mass ** (1. / d_size))
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
        An estimation of D calculated from Sigma. It's based on a 15th order polynomial fit of
        the output from the `sigma2D` function. No value of D yields error >0.1%.
    """
    d_size = calcDSize(raw_rms, noise, NAi)
    # These are the polynomical coefficients stored in the SimgaToD_coefs.mat file. They go from high order to low, E.G. x^2 + x + 1
    sigmaToD_coefs = [-9.14414809736752e-09, 8.02336561707375e-07, -3.22276589702395e-05, 0.000784980326922923, -0.0129458554989855, 0.152852475387947,
                      -1.33210715342735, 8.70614624955508, -42.9149123685218, 159.111116839950, -438.829185621276, 881.674160348790, -1246.22822358504,
                      1168.11294529161, -647.810667596662, 161.021813781994]
    sigmaToD_coefs = np.array(list(reversed(sigmaToD_coefs)))  # The order of the coefficients is different than in matlab
    d_estimate = np.polynomial.polynomial.polyval(d_size, sigmaToD_coefs)
    d_estimate[d_size > 10] = 2.99  # The fitting doesn't work well at very high values of D_size.
    return d_estimate


if __name__ == '__main__':
    import time
    testData = np.linspace(0.001, 0.1, num=100)
    stime = time.time()
    exact = sigma2D(testData, 0.009, 0.55)
    estimate = sigma2DApproximation(testData, 0.009, 0.55)
    ftime = time.time() - stime  # Execution time of the function
    a = 1