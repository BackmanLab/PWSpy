from pwspy.imCube import DynCube

outPath = r''
refPath = r''

ref = DynCube.loadAny(refPath)
ref.data[:, :, :] = ref.data.mean(axis=2)[:, :, None]
ref.toFile(outPath)
