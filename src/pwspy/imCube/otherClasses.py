# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""

import typing



class CameraCorrection(typing.NamedTuple):
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.List[float] = None