import numpy as np

def checkMeanReflectance(r: np.ndarray):
    assert len(r.shape) == 2
    avg = r.mean()
    if avg > 1.5:
        return AnalysisWarning
    else:
        return None

def checkMeanSpectraRatio():
    pass
def checkRSquared():
    pass

class AnalysisWarning:
    pass