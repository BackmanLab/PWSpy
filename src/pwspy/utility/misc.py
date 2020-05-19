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
Objects that are generally useful in python programming.

Decorators
-------------
.. autosummary::
   :toctree: generated/

   cached_property
   profileDec
"""

class cached_property(object):
    """
    A decorator for a property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76

    Todo:
        This is probably better implemented by cachetools.LRUCache
    """


    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def profileDec(filePath: str):
    """
    A decorator to profile a function call using cProfile

    Args:
        filePath: cProfile will dump a log file to this location.
    """
    def innerDec(func):
        import cProfile
        def newFunc(*args, **kwargs):
            pr = cProfile.Profile()
            pr.enable()
            ret = func(*args, **kwargs)
            pr.disable()
            pr.dump_stats(filePath)
            # after your function ends
            # pr.print_stats(sort=sort)
            return ret
        return newFunc
    return innerDec