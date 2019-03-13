import numpy as np

def acf(d, lmin, lmax, x):
    out = ((3-d) .* ((((lmin.^4) .* ((lmin./lmax).^(-1.*d)) .* vpa(expint(-2+d, sym(x./lmax))))./(lmax.^3))...
    - lmin .* vpa(expint(-2+d, sym(x./lmin))))) ./ (lmin.*(1 - (lmin./lmax).^(3-d)));

def acfd(d, lmin, lmax):
    delta = 0.1;
    out = 3 + (log(acf(d, lmin, lmax, (lmax+lmin)./100 + delta)) - ...
        log(acf(d, lmin, lmax, (lmax+lmin)./100)))./ ...
        (log((lmax+lmin)./100 + delta) - log((lmax+lmin)./100));

def calcDSize(system: str, system_correction: float, raw_rms: np.ndarray):
    if system == 'storm':
        sigma = np.real(np.sqrt(raw_rms**2 - .012**2)) * system_correction
        d_size = sigma * 5.55 + 1.473

    elif system == 'live' or system == 'lcpws1':
        sigma = np.real(np.sqrt(raw_rms**2 - .009**2)) * system_correction
        d_size = sigma * 7.67 + 1.473
    else: raise NameError("No valid system found")
    return d_size

def  SigmaToD(d_size: np.ndarray):
    mf = 1000000
    d_size[d_size == 3] = 3.00001

    lmaxlminapprox = 100
    correction = ((3 - d_size) * (1 - (lmaxlminapprox ^ (-1. * d_size)))) / (
                d_size * (1 - (lmaxlminapprox ^ (d_size - 3))))
    mass = mf / correction

    d_exact = acfd(d_size, 1, mass**(1. / d_size))

    return d_exact

def sigma2DApprox(d_size):
    d_estimate = 3 * (1 - np.exp(-(d_size / 3)**7))**(1 / 7)
    return d_estimate