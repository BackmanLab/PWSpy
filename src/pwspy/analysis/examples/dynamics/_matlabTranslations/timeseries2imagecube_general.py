from pwspy.dataTypes._data import DynCube

outPath = r''
refPath = r''

ref = DynCube.loadAny(refPath)
ref.data[:, :, :] = ref.data.mean(axis=2)[:, :, None] #The reference should be static over time. Take the mean to filter out all noise.
#TODO we should save or report the noise level as well.
ref.toFile(outPath)
