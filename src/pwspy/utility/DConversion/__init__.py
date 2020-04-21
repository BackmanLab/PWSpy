import numpy as np
from scipy.integrate import quad
# TODO see email from self (nicholas.anthony@northwestern.edu) on 3/26/2019 showing how the equations can be simplified to be more efficient)


@np.vectorize
def expn(n: float, x: float):
    """This is a custom implementation of the generalized exponential exponential integral `En`. The implementation in `scipy.special.expn` is faster but only supports
    integers for `n`.

    Args:
        n: :todo:
        x: :todo:
    """
    def integrand(t: float, n: float, x: float):
        return np.exp(-x*t) / t**n #TODO this doesn't looks like the def in scipy, is it right?
    return quad(integrand, 1, np.inf, args=(n, x))[0]


def acf(d, lmin, lmax, x):
    out = ((3 - d) * ((((lmin**4) * ((lmin / lmax)**(-d)) * expn(-2 + d, x / lmax)) / (lmax**3)) - lmin * expn(-2 + d, x / lmin))) / (lmin * (1 - (lmin / lmax)**(3-d)))
    return out


def acfd(d, lmin, lmax):
    delta = 0.1
    x = (lmax+lmin) / 100
    out = 3 + (np.log(acf(d, lmin, lmax, x + delta)) - np.log(acf(d, lmin, lmax, x))) / (np.log(x + delta) - np.log(x))
    return out


def calcDSize(raw_rms: np.ndarray, noise: float, NAi: float):
    """
    Default values:
        storm: noise=0.012m
        lcpws1: noise=0.009

    Args:
        raw_rms:
        noise:
        NAi:

    Returns:

    MATLAB COMMENT:
        %
        % DESCRIPTION
        %   This function will convert RMS values to D using one or two different
        %   methods. This function requires acfd.m, acf_1.m and SigmaToD_coefs.mat
        %   to function properly.
        %
        % INPUT ARGUMENTS
        %   raw_rms:
        %       The rms values you with to convert (e.g., cubeRms).
        %   system_correction:
        %       Optional input for the correction factor required to convert RMS to
        %       Sigma due to extra reflections in the microscope. The default is [2.43].
        %   NAi:
        %       Optional input for the illumination numerical aperture (NA) of the
        %       objective. The default is [0.55].
        %   noise:
        %       Optional input for the background noise in the system (i.e., RMS of
        %       the glass). The default [0.009].
        %   option:
        %       Optional input to tell the function to only run the approximation
        %       method. Alternatively, the user can define this by limiting the
        %       output arguments. The default is [] and the alternative option is
        %       ['approximation only'] or ['approx'].
        %
        % OUTPUT ARGUMENTS
        %   d_estimate:
        %       This is an estimation of D calculated from Sigma. It's based on a
        %       15th order polynomial fit of d_exact. No value of D yields error >0.1%.
        %   d_exact:
        %       Optional output for calculating more exact solution of D from Sigma.
        %       This calculation is based on derivations by Vadim Backman.
        %
        % EXAMPLES
        %   [d_estimate, d_exact] = SigmaToD(0.1, [], [], 0.005 , 'approximation only')
        %   [d_estimate, d_exact] = SigmaToD(cubeRms, 2, 0.45);
        %   d_estimate = SigmaToD(cubeRms);
        %
        % REFERENCES
        %   L. Cherkezyan, D. Zhang, H. Subramanian, I. Capoglu, A. Taflove,
        %   V. Backman, "Review of interferometric spectroscopy of scattered light
        %   for the quantification of subdiffractional structure of biomaterials."
        %   J. of Biomedical Optics, 22(3), 030901 (2017).
        %
        %
        % Author: Adam Eshein (aeshein@u.northwestern.edu) 3.14.2019
        %   Based on Mathematica code written by Vadim Backman (v-backman@northwestern.edu)

    """
    sigma = np.real(np.sqrt(raw_rms**2 - noise**2))
    d_size = sigma * 13.8738 * NAi + 1.473
    return d_size


def sigma2D(d_size: np.ndarray):
    #This runs 6 times faster than the matlab version for some reason
    mf = 1000000
    d_size[d_size == 3] = 3.00001

    lmaxlminapprox = 100
    correction = ((3 - d_size) * (1 - (lmaxlminapprox**(-1. * d_size)))) / (
                d_size * (1 - (lmaxlminapprox**(d_size - 3))))
    mass = mf / correction
    d_exact = acfd(d_size, 1, mass**(1. / d_size))
    return d_exact


def sigma2DApprox2(d_size: np.ndarray) -> np.ndarray:
    # These are the polynomical coefficients stored in the SimgaToD_coefs.mat file. They go from high order to low, E.G. x^2 + x + 1
    sigmaToD_coefs = [-9.14414809736752e-09, 8.02336561707375e-07, -3.22276589702395e-05, 0.000784980326922923, -0.0129458554989855, 0.152852475387947,
                      -1.33210715342735, 8.70614624955508, -42.9149123685218, 159.111116839950, -438.829185621276, 881.674160348790, -1246.22822358504,
                      1168.11294529161, -647.810667596662, 161.021813781994]
    d_estimate = np.polynomial.polyval(sigmaToD_coefs, d_size) # Note do not confuse this with np.polynomial.polynomial.polyval(), the ordering is different.
    d_estimate[d_size > 10] = 2.99  # The fitting doesn't work well at very high values of D_size.
    return d_estimate

def testexpn():
    lmin=1
    d=np.array([2.1796160,2.9585142,2.6632771,1.8785352,1.8430616])
    x=np.array([8.8774614,2.6083560,3.6681373,20.619408,23.234888])
#    d=d[1]
#    x=x[1]
    res = expn(-2+d, x/lmin)
    return res