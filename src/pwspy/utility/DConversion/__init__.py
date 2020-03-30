import numpy as np
from scipy.integrate import quad
# TODO wait till adam posts somewhat final matlab code and update from that. Then see email from self (nicholas.anthony@northwestern.edu) on 3/26/2019 showing how the equations can be simplified to be more efficient)


def myexpn(n, x):
    #this is needed since scipy.special.expn only accepts integers for n
    def integrand(t, n, x):
        return np.exp(-x*t) / t**n
    return quad(integrand, 1, np.inf, args=(n, x))[0]
expn = np.vectorize(myexpn)

def acf(d, lmin, lmax, x):
    out = ((3 - d) * ((((lmin**4) * ((lmin / lmax)**(-d)) * expn(-2 + d, x / lmax)) / (lmax**3)) - lmin * expn(-2 + d, x / lmin))) / (lmin * (1 - (lmin / lmax)**(3-d)))
    return out

def acfd(d, lmin, lmax):
    delta = 0.1
    x = (lmax+lmin) / 100
    out = 3 + (np.log(acf(d, lmin, lmax, x + delta)) - np.log(acf(d, lmin, lmax, x))) / (np.log(x + delta) - np.log(x))
    return out

def calcDSize(system: str, system_correction: float, raw_rms: np.ndarray):
    if system == 'storm':
        sigma = np.real(np.sqrt(raw_rms**2 - .012**2)) * system_correction
        d_size = sigma * 5.55 + 1.473

    elif system == 'live' or system == 'lcpws1':
        sigma = np.real(np.sqrt(raw_rms**2 - .009**2)) * system_correction
        d_size = sigma * 7.67 + 1.473
    else: raise NameError("No valid system found")
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

def sigma2DApprox(d_size):
    d_estimate = 3 * (1 - np.exp(-(d_size / 3)**7))**(1 / 7)
    return d_estimate

def testexpn():
    lmin=1
    d=np.array([2.1796160,2.9585142,2.6632771,1.8785352,1.8430616])
    x=np.array([8.8774614,2.6083560,3.6681373,20.619408,23.234888])
#    d=d[1]
#    x=x[1]
    res = expn(-2+d, x/lmin)
    return res