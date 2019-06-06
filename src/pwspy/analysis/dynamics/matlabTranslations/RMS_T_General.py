from pwspy.imCube import DynCube
import os
from glob import glob

wDir = r''
refPath = r''
frameAverage = False
sizeAverage = 3

ref = DynCube.loadAny(refPath)
ref.correctCameraEffects(auto=True)
ref.normalizeByExposure()

files = glob(os.path.join(wDir, 'Cell*'))
for f in files:
    dyn = DynCube.loadAny(f)
    dyn.correctCameraEffects(auto=True)
    dyn.normalizeByExposure()
    dyn.normalizeByReference(ref)
