import os
from glob import glob
from typing import List
import json
from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess
from pwspy.utility.reflectanceHelper import Material
import pwspy.apps.ExtraReflectanceCreator.extraReflectance  as er #import prepareData, plotExtraReflection, saveRExtra
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib import animation
import traceback
import random

class ERWorkFlow:
    @staticmethod
    def _splitPath(path: str) -> List[str]:
        folders = []
        while 1:
            path, folder = os.path.split(path)
            if folder != "":
                folders.append(folder)
            else:
                if path != "":
                    folders.append(path)
                break
        return folders

    @staticmethod
    def _processIm(im: ImCube, camCorrection: CameraCorrection, binning: int) -> ImCube:
        im.correctCameraEffects(camCorrection, binning=binning)
        im.normalizeByExposure()
        im.filterDust(6)  # TODO change units
        return im

    @staticmethod
    def scanDirectory(directory: str) -> pd.DataFrame:
        try:
            cam = CameraCorrection.fromJsonFile(os.path.join(directory, 'cameraCorrection.json'))
        except Exception as e:
            print(e)
            raise Exception(f"Could not load a camera correction at {directory}")
        files = glob(os.path.join(directory, '*', '*', 'Cell*'))
        rows = []
        matMap = {'air': Material.Air, 'water': Material.Water, 'ipa': Material.Ipa, 'ethanol': Material.Ethanol}
        for file in files:
            filelist = ERWorkFlow._splitPath(file)
            s = filelist[2]
            m = matMap[filelist[1]]
            rows.append({'setting': s, 'material': m, 'cube': file})
        df = pd.DataFrame(rows)
        return df

    @staticmethod
    def loadCubes(df: pd.DataFrame, includeSettings: List[str], binning: int):
        df = df[df['setting'].isin(includeSettings)]
        cubes = loadAndProcess(df, ERWorkFlow._processIm, parallel=True, procArgs=[self.cameraCorrection, binning])
        return cubes

    @staticmethod
    def plot(cubes: pd.DataFrame, saveToPdf: bool = False):
        settings = set(cubes['setting'])  # Unique setting values
        materials = set(cubes['material'])
        theoryR = er.getTheoreticalReflectances(materials, cubes['cube'][0].wavelengths)  # Theoretical reflectances
        matCombos = er.generateMaterialCombos(materials)

        print("Select an ROI")
        mask = random.choice(cubes['cube']).selectLassoROI()  # Select an ROI to analyze
        meanValues, allCombos = er.prepareData(cubes, settings, matCombos, theoryR, mask)

        er.plotExtraReflection(allCombos, meanValues, theoryR, matCombos, settings)
        if saveToPdf:
            with PdfPages(os.path.join(directory, "figs.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)

    @staticmethod
    def save():
        pass

    @staticmethod
    def compareDates(cubes: pd.DataFrame):
        anis = []
        mask = random.choice(cubes['cube']).selectLassoRoi()
        for mat in set(cubes['material']):
            c = cubes[cubes['material'] == mat]
            fig, ax = plt.subplots()
            fig.suptitle(mat)
            fig2, ax2 = plt.subplots()
            fig2.suptitle(mat)
            anims = []
            for i, row in c.iterrows():
                im = row['cube']
                spectra = im.getMeanSpectra(mask)[0]
                ax.plot(im.wavelengths, spectra, label=row['setting'])
                anims.append((ax2.imshow(im.data.mean(axis=2), animated=True,
                                         clim=[np.percentile(im.data, .5), np.percentile(im.data, 99.5)]),
                              ax2.text(200, 100, row['setting'])))
            ax.legend()
            anis.append(animation.ArtistAnimation(fig2, anims, interval=1000, blit=False))
