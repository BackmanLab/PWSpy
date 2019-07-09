from pwspy.dataTypes import DynCube
import os
from glob import glob

wDir = r''
refPath = r''

ref = DynCube.loadAny(refPath)
ref.correctCameraEffects(auto=True)
ref.normalizeByExposure()

files = glob(os.path.join(wDir, 'Cell*'))
for f in files:
    dyn = DynCube.loadAny(f)
    dyn.correctCameraEffects(auto=True)
    dyn.normalizeByExposure()
    dyn.normalizeByReference(ref)

    #TODO the original script optionally uses 3 frame frame-averaging here as a lowpass

    #This is equivalent to subtracting the mean from each spectra and taking the RMS
    rms = dyn.data.std(axis=2)

    #TODO save the RMS