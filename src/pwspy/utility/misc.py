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