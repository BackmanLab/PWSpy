import hashlib
import os
from datetime import datetime
from glob import glob
from typing import List, Any, Dict
import json

from PyQt5.QtWidgets import QWidget
from matplotlib import animation

from pwspy.dataTypes import CameraCorrection, AcqDir, ICMetaData, ImCube
from pwspy.apps.ExtraReflectanceCreator.widgets.dialog import IndexInfoForm
from pwspy.dataTypes import Roi
from pwspy import dateTimeFormat
from pwspy.utility.reflection import Material
from pwspy.utility.fileIO import loadAndProcess
import pwspy.utility.reflection.extraReflectance  as er
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def _splitPath(path: str) -> List[str]:
    """Utility function. Given a string representing a file path this function will return a list of strings, each list
    item representing a single level of the file path."""
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


def scanDirectory(directory: str) -> Dict[str, Any]:
    try:
        cam = CameraCorrection.fromJsonFile(os.path.join(directory, 'cameraCorrection.json'))
    except Exception as e:
        print(e)
        raise Exception(f"Could not load a camera correction at {directory}")
    files = glob(os.path.join(directory, '*', '*', 'Cell*'))
    rows = []
    matMap = {'air': Material.Air, 'water': Material.Water, 'ipa': Material.Ipa, 'ethanol': Material.Ethanol, 'glass': Material.Glass}
    for file in files:
        filelist = _splitPath(file)
        s = filelist[2]
        m = matMap[filelist[1]]
        file = AcqDir(file).pws.filePath # old pws is saved directly in the "Cell{X}" folder. new pws is saved in "Cell{x}/PWS" the acqDir class helps us abstract that out and be compatible with both.
        rows.append({'setting': s, 'material': m, 'cube': file})
    df = pd.DataFrame(rows)
    return {'dataFrame': df, 'camCorrection': cam}


def _processIm(im: ImCube, args) -> ImCube:
    im.correctCameraEffects(**args)
    im.normalizeByExposure()
    try:
        im.filterDust(0.8)  # in microns
    except ValueError:
        print("No pixel size metadata found. assuming a gaussian filter radius of 6 pixels = 1 sigma.")
        im.filterDust(6, pixelSize=1) #Do the filtering in units of pixels if no auto pixelsize was found
    return im


class ERWorkFlow:
    """This class serves as an adapter between the complication operations available in the pwspy.utility.relfection.extraReflectance module and the UI of the ERCreator app."""
    def __init__(self, workingDir: str, homeDir: str):
        self.cubes = self.fileStruct = self.df = self.cameraCorrection = self.currDir = self.plotnds = self.anims = None
        self.figs = []
        self.homeDir = homeDir
        # generateFileStruct:
        folders = [i for i in glob(os.path.join(workingDir, '*')) if os.path.isdir(i)]
        settings = [os.path.split(i)[-1] for i in folders]
        fileStruct = {}
        for f, s in zip(folders, settings):
            fileStruct[s] = scanDirectory(f)
        self.fileStruct = fileStruct

    def invalidateCubes(self):
        self.cubes = None

    def deleteFigures(self):
        for fig in self.figs:
            if isinstance(fig, plt.Figure):
                plt.close(fig)
            elif isinstance(fig, QWidget):
                fig.close()
            else:
                raise TypeError(f"Type {type(fig)} shouldn't be here, what's going on?")
        self.figs = []

    def loadCubes(self, includeSettings: List[str], binning: int, parallelProcessing: bool):
        df = self.df[self.df['setting'].isin(includeSettings)]
        if binning is None:
            args = {'correction': None, 'binning': None}
            for cube in df['cube']:
                md = ICMetaData.loadAny(cube)
                if md.binning is None:
                    raise Exception("No binning metadata found. Please specify a binning setting.")
                elif md.cameraCorrection is None:
                    raise Exception("No camera correction metadata found. Please specify a binning setting, in this case the application will use the camera correction stored in the cameraCorrection.json file of the calibration folder")
        else:
            args = {'correction': self.cameraCorrection, 'binning': binning}
        self.cubes = loadAndProcess(df, _processIm, parallel=parallelProcessing, procArgs=[args])

    def plot(self, numericalAperture: float, saveToPdf: bool = False, saveDir: str = None):
        cubes = self.cubes
        settings = set(cubes['setting'])  # Unique setting values
        materials = set(cubes['material'])
        theoryR = er.getTheoreticalReflectances(materials,
                                                cubes['cube'].iloc[0].wavelengths, numericalAperture)  # Theoretical reflectances
        matCombos = er.generateMaterialCombos(materials)

        print("Select an ROI")
        verts = cubes['cube'].sample(n=1).iloc[0].selectLassoROI()  # Select an ROI to analyze
        mask = Roi.fromVerts('doesntmatter', 1, verts, cubes['cube'].sample(n=1).iloc[0].data.shape[:-1])
        self.figs.extend(er.plotExtraReflection(cubes, theoryR, matCombos, numericalAperture, mask, plotReflectionImages=True))  # TODO rather than opening a million new figures open a single window that lets you flip through them.
        if saveToPdf:
            with PdfPages(os.path.join(saveDir, f"fig_{datetime.strftime(datetime.now(), '%d-%m-%Y %HH%MM%SS')}.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)

    def save(self, numericalAperture: float):
        settings = set(self.cubes['setting'])
        for setting in settings:
            cubes = self.cubes[self.cubes['setting'] == setting]
            materials = set(cubes['material'])
            theoryR = er.getTheoreticalReflectances(materials,
                                                    cubes['cube'].iloc[0].wavelengths, numericalAperture)  # Theoretical reflectances
            matCombos = er.generateMaterialCombos(materials)
            combos = er.getAllCubeCombos(matCombos, cubes)
            erCube, rExtraDict, self.plotnds = er.generateRExtraCubes(combos, theoryR, numericalAperture)
            print(f"Final data max is {erCube.data.max()}")
            print(f"Final data min is {erCube.data.min()}")
            self.figs.extend(self.plotnds) # keep track of opened figures.
            saveName = f'{self.currDir}-{setting}'
            dialog = IndexInfoForm(f'{self.currDir}-{setting}', erCube.metadata.idTag)
            self.saveParams = {'dlg': dialog, 'ercube': erCube, 'savename': saveName} #We save this to a varaible so it can be accessed by the callback for an accepted dialog.
            dialog.accepted.connect(self.saveERDialogAccepted)
            dialog.show()

    def saveERDialogAccepted(self):
        dialog = self.saveParams['dlg']; erCube = self.saveParams['ercube']; saveName = self.saveParams['savename']
        erCube.metadata.inheritedMetadata['description'] = dialog.description
        erCube.toHdfFile(self.homeDir, saveName)
        self.updateIndex(saveName, erCube.metadata.idTag, dialog.description, erCube.metadata.dirName2Directory('', saveName))

    def updateIndex(self, saveName: str, idTag: str, description: str, filePath: str):
        with open(os.path.join(self.homeDir, 'index.json'), 'r') as f:
            index = json.load(f)
        md5hash = hashlib.md5()
        with open(os.path.join(self.homeDir, filePath), 'rb') as f:
            md5hash.update(f.read())
        md5 = md5hash.hexdigest() #The md5 checksum as a string of hex.
        cubes = index['reflectanceCubes']
        newEntry = {'fileName': filePath,
                    'description': description,
                    'idTag': idTag,
                    'name': saveName,
                    'md5': md5}
        cubes.append(newEntry)
        index['reflectanceCubes'] = cubes
        index['creationDate'] = datetime.strftime(datetime.now(), dateTimeFormat)
        with open(os.path.join(self.homeDir, 'index.json'), 'w') as f:
            json.dump(index, f, indent=4)

    def compareDates(self):
        anis = []
        figs = []
        verts = self.cubes['cube'].sample(n=1).iloc[0].selectLassoROI()
        mask = Roi.fromVerts('doesntmatter', 1, verts=verts,
                             dataShape=self.cubes['cube'].sample(n=1).iloc[0].data.shape[:-1])
        for mat in set(self.cubes['material']):
            c = self.cubes[self.cubes['material'] == mat]
            fig, ax = plt.subplots()
            fig.suptitle(mat.name)
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Counts/ms")
            fig2, ax2 = plt.subplots()
            fig2.suptitle(mat.name)
            figs.extend([fig, fig2])
            anims = []
            for i, row in c.iterrows():
                im = row['cube']
                spectra = im.getMeanSpectra(mask)[0]
                ax.plot(im.wavelengths, spectra, label=row['setting'])
                anims.append((ax2.imshow(im.data.mean(axis=2), animated=True,
                                         clim=[np.percentile(im.data, .5), np.percentile(im.data, 99.5)]),
                              ax2.text(40, 40, row['setting'])))
            ax.legend()
            anis.append(animation.ArtistAnimation(fig2, anims, interval=1000, blit=False))
        self.anims = anis

        self.figs.extend(figs) #Keep track of opened figures.

    def directoryChanged(self, directory: str):
        self.currDir = directory
        _ = self.fileStruct[directory]
        self.df = _['dataFrame']
        self.cameraCorrection = _['camCorrection']
        self.invalidateCubes()
