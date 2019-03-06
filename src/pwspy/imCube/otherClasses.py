# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""

import typing
from dataclasses import dataclass


@dataclass(frozen=True)
class CameraCorrection:
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.Tuple[float] = None

    def __post_init__(self):
        assert isinstance(self.linearityPolynomial, tuple)