from pwspy.imCube import ICBase
import numpy as np

class DynCube(ICBase):
    def __init__(self, data, metadata: ICMetaData, dtype=np.float32):
        assert isinstance(metadata, ICMetaData)
        self.metadata = metadata
        ICBase.__init__(self, data, self.metadata.times, dtype=dtype)

    @property
    def times(self):
        return self.index
    