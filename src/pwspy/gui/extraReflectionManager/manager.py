import os
from glob import glob

from pwspy import ExtraReflectanceCube


class ERManager:
    def __init__(self, filePath: str):
        self.directory = filePath
        files = glob(os.path.join(self.directory, f'*{ExtraReflectanceCube.fileSuffix}'))
        files = [(f, ExtraReflectanceCube.validPath(f)) for f in files]
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
