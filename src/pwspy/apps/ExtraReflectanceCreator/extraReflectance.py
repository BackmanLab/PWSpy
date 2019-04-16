from typing import Dict, List, Tuple, Iterable, Any, Sequence, Iterator, Union, Optional

from pwspy import ImCube, ExtraReflectanceCube
from pwspy.imCube.otherClasses import Roi
from pwspy.utility.reflectanceHelper import Material, getReflectance
import itertools
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
import pandas as pd
from dataclasses import dataclass, fields
from matplotlib import animation
import scipy.signal as sps
from pwspy.utility.PlotNd import PlotNd
MCombo = Tuple[Material, Material]


class CubeCombo:
    def __init__(self, material1: Material, material2: Material, cube1: ImCube, cube2: ImCube):
        self.mat1 = material1
        self.mat2 = material2
        self.data1 = cube1
        self.data2 = cube2

    def keys(self) -> MCombo:
        return self.mat1, self.mat2

    def values(self) -> Tuple[ImCube, ImCube]:
        return self.data1, self.data2

    def items(self) -> Iterator[Tuple[Material, ImCube]]:
        return zip(self.keys(), self.values())

    def __getitem__(self, item: Material) -> ImCube:
        if item == self.mat1:
            return self.data1
        elif item == self.mat2:
            return self.data2
        else:
            raise KeyError("Key must be either mat1 or mat2.")


@dataclass
class ComboSummary:
    mat1Spectra: np.ndarray
    mat2Spectra: np.ndarray
    combo: CubeCombo
    rExtra: np.ndarray
    I0: np.ndarray
    cFactor: float


def _interpolateNans(arr):
    """Interpolate out nan values along the third axis of an array"""

    def interp1(arr1):
        nans = np.isnan(arr1)
        f = lambda z: z.nonzero()[0]
        arr1[nans] = np.interp(f(nans), f(~nans), arr1[~nans])
        return arr1

    arr = np.apply_along_axis(interp1, 2, arr)
    return arr

def getTheoreticalReflectances(materials: Iterable[Material], index: Tuple[float]) -> Dict:
    """Generate a dictionary containing a pandas series of the `material`-glass reflectance for each material in
    `materials`. Index is in units of nanometers."""
    theoryR = {}
    for material in materials:  # For each unique material in the `cubes` list
        theoryR[material] = getReflectance(material, Material.Glass, index=index)
    return theoryR


def generateMaterialCombos(materials: Iterable[Material], excludedCombos: Iterable[MCombo] = None) -> List[MCombo]:
    """Given a list of material strings and a list of material combination tuples that should be skipped, this function returns
    a list of all possible material combo tuples"""
    if excludedCombos is None:
        excludedCombos = []
    matCombos = list(itertools.combinations(materials, 2))  # All the combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Remove excluded combinations.
    for i, (m1, m2) in enumerate(matCombos):  # Make sure to arrange materials so that our reflectance ratio is greater than 1
        if (getReflectance(m1, Material.Glass) / getReflectance(m2, Material.Glass)).mean() < 1:
            matCombos[i] = (m2, m1)
    return matCombos


def getAllCubeCombos(matCombos: Iterable[MCombo], df: pd.DataFrame) -> Dict[MCombo, List[CubeCombo]]:
    """Given a list of material combo tuples, return a dictionary whose keys are the material combo tuples and whose values are
    lists of CubeCombos."""
    allCombos = {}
    for matCombo in matCombos:
        matCubes = {material: df[df['material'] == material]['cube'] for material in matCombo}  # A dictionary sorted by material containing lists of the ImCubes that are relevant to this loop..
        allCombos[matCombo] = [CubeCombo(*matCubes.keys(), *combo) for combo in itertools.product(*matCubes.values())]
    return allCombos


def calculateSpectraFromCombos(cubeCombos: Dict[MCombo, List[CubeCombo]], theoryR: dict, mask: Roi = None) ->\
        Tuple[Dict[Union[MCombo, str], Dict[str, Any]], Dict[MCombo, List[ComboSummary]]]:
    """Expects a dictionary as created by `getAllCubeCombos` and a dictionary of theoretical reflections.

    This is used to examine the output of extra reflection calculation before using saveRExtra to save a cube for each setting.
    Returns a dictionary containing
    """

    # Save the results of relevant calculations to a dictionary, this dictionary will be returned to the user along with
    # the raw data, `allCombos`
    allCombos = {}
    meanValues = {}
    params = ['rExtra', 'I0', 'mat1Spectra', 'mat2Spectra', 'cFactor']
    for matCombo in cubeCombos.keys():
        allCombos[matCombo] = []
        for combo in cubeCombos[matCombo]:
            mat1, mat2 = combo.keys()
            c = ComboSummary(mat1Spectra=combo[mat1].getMeanSpectra(mask)[0],
                             mat2Spectra=combo[mat2].getMeanSpectra(mask)[0],
                             rExtra=None,
                             I0=None,
                             cFactor=None,
                             combo=combo)
            c.rExtra = ((theoryR[mat1] * c.mat2Spectra) - (theoryR[mat2] * c.mat1Spectra)) / (c.mat1Spectra - c.mat2Spectra)
            c.I0 = c.mat2Spectra / (theoryR[mat2] + c.rExtra)
            c.cFactor = (c.rExtra.mean() + theoryR[Material.Water].mean()) / theoryR[Material.Water].mean()
            allCombos[matCombo].append(c)
        meanValues[matCombo] = {
                param: np.array(list(
                        [getattr(combo, param) for combo in allCombos[matCombo]])).mean(axis=0) for param in params}
    meanValues['mean'] = {param: np.array(list([meanValues[matCombo][param] for matCombo in cubeCombos.keys()])).mean(axis=0) for param in params}
    return meanValues, allCombos


def plotExtraReflection(df: pd.DataFrame, theoryR: dict, matCombos:List[MCombo], mask: Optional[Roi] = None, plotReflectionImages: bool = False) -> List[plt.Figure]:

    settings = set(df['setting'])

    meanValues: Dict[str, Dict[Union[MCombo, str], Dict[str, Any]]] = {}
    allCombos: Dict[str, Dict[MCombo, List[ComboSummary]]] = {}
    for sett in settings:
        cubeCombos = getAllCubeCombos(matCombos, df[df['setting'] == sett])
        meanValues[sett], allCombos[sett] = calculateSpectraFromCombos(cubeCombos, theoryR, mask)
    figs = []
    fig, ax = plt.subplots()  # For extra reflections
    fig.suptitle("Extra Reflection")
    figs.append(fig)
    ax.set_ylabel("%")
    ax.set_xlabel("nm")
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo.combo
                ax.plot(cubes[mat1].wavelengths, combo.rExtra,
                        label=f'{sett} {mat1}:{int(cubes[mat1].metadata["exposure"])}ms {mat2}:{int(cubes[mat2].metadata["exposure"])}ms')
        ax.plot(cubes[mat1].wavelengths, meanValues[sett]['mean']['rExtra'], color='k', label=f'{sett} mean')
    ax.legend()

    fig2, ratioAxes = plt.subplots(nrows=len(matCombos))  # for correction factor
    figs.append(fig2)
    if not isinstance(ratioAxes, np.ndarray): ratioAxes = np.array(ratioAxes).reshape(
        1)  # If there is only one axis we still want it to be a list for the rest of the code
    ratioAxes = dict(zip(matCombos, ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0].name}/{combo[1].name} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]] / theoryR[combo[1]], label='Theory')
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo.combo
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, combo.mat1Spectra / combo.mat2Spectra,
                                         label=f'{sett} {mat1.name}:{int(cubes[mat1].metadata["exposure"])}ms {mat2.name}:{int(cubes[mat2].metadata["exposure"])}ms')
    [ratioAxes[combo].legend() for combo in matCombos]

    for sett in settings:
        means = meanValues[sett]['mean']

        fig3, scatterAx = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        fig3.suptitle(sett)
        figs.append(fig3)
        scatterAx.set_ylabel("Theoretical Ratio")
        scatterAx.set_xlabel("Observed Ratio w/ cFactor")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [means['cFactor'] * (
                meanValues[sett][matCombo]['mat1Spectra'] / meanValues[sett][matCombo]['mat2Spectra']).mean() for
                          matCombo in matCombos]
        [scatterAx.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx.plot(x, x, label='1:1')
        scatterAx.legend()

        fig4, scatterAx2 = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        fig4.suptitle(sett)
        figs.append(fig4)
        scatterAx2.set_ylabel("Theoretical Ratio")
        scatterAx2.set_xlabel("Observed Ratio after Subtraction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [((meanValues[sett][matCombo]['mat1Spectra'] - means['I0'] * means['rExtra']) / (
                meanValues[sett][matCombo]['mat2Spectra'] - means['I0'] * means['rExtra'])).mean() for matCombo in
                          matCombos]
        [scatterAx2.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx2.plot(x, x, label='1:1')
        scatterAx2.legend()

        if plotReflectionImages:
            for matCombo in matCombos:
                mat1, mat2 = matCombo
                for combo in allCombos[sett][matCombo]:
                    cubes = combo.combo
                    fig5 = plt.figure()
                    figs.append(fig5)
                    plt.title(f"Reflectance %. {sett}, {mat1}:{int(cubes[mat2].metadata['exposure'])}ms, {mat2}:{int(cubes[mat2].metadata['exposure'])}ms")
                    _ = ((theoryR[mat1][np.newaxis, np.newaxis, :] * cubes[mat2].data) - (
                        theoryR[mat2][np.newaxis, np.newaxis, :] * cubes[mat1].data)) / (
                            cubes[mat1].data - cubes[mat2].data)
                    _[np.isinf(_)] = np.nan
                    if np.any(np.isnan(_)):
                        _ = _interpolateNans(_)  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
                    refIm = _.mean(axis=2)
                    plt.imshow(refIm, vmin=np.percentile(refIm, .5), vmax=np.percentile(refIm, 99.5))
                    plt.colorbar()

        print(f"{sett} correction factor")
        print(means['cFactor'])
    return figs


def generateOneRExtraCube(combo: CubeCombo, theoryR: dict, correctErrors: bool) -> np.ndarray:
    def recursiveClean(arr: np.ndarray) -> np.array:
        def getInvalids(arr: np.ndarray) -> int:
            arr[np.isinf(arr)] = np.nan
            nans = np.isnan(arr).sum()
            nans += (arr > 1).sum()
            arr[arr > 1] = 1
            nans += (arr < 0).sum()
            arr[arr < 0] = 0
            return nans

        def blur(arr: np.ndarray) -> np.ndarray:
            """Blur a 3d array along the first two axes."""
            def _gaussKernel(radius: int):
                # A kernel that goes to 1 std. It would be better to go out to 2 or 3 std but then you need a larger kernel which greatly increases convolution time.
                lenSide = 1 + 2 * radius
                side = np.linspace(-1, 1, num=lenSide)
                X, Y = np.meshgrid(side, side)
                R = np.sqrt(X ** 2 + Y ** 2)
                k = np.exp(-(R ** 2) / 2)
                k = k / k.sum()  # normalize so the total is 1.
                return k
            kernel = _gaussKernel(6)
            for i in range(arr.shape[2]):
                m = arr[:, :,i].mean()  # By subtracting the mean and then adding it after convolution we are effectively padding the convolution with the mean.
                arr[:, :, i] = sps.convolve(arr[:, :, i] - m, kernel, mode='same') + m
            return arr

        invlds = getInvalids(arr)
        if invlds > 0:
            print(f"{invlds} ({invlds / arr.size * 100}%) invalid values detected in ({combo.mat1.name}, {combo.mat2.name}). Interpolating and blurring")
            if np.isnan(arr).sum() > 0:
                arr = _interpolateNans(arr)
            print("Done interpolating.")
            arr = blur(arr)
            print("Done blurring.")
            return recursiveClean(arr)
        else:
            return arr

    denominator = combo.data1.data - combo.data2.data
    nominator1 = np.array(theoryR[combo.mat1][np.newaxis, np.newaxis, :]) * combo.data2.data
    nominator2 = np.array(theoryR[combo.mat2][np.newaxis, np.newaxis, :]) * combo.data1.data
    arr = (nominator1 - nominator2) / denominator
    if correctErrors:
        arr = recursiveClean(arr)
    return arr



def generateRExtraCubes(allCombos: Dict[MCombo, List[CubeCombo]], theoryR: dict) -> Tuple[ExtraReflectanceCube, Dict[Union[str, MCombo], np.array], List[PlotNd]]:
    """Expects a dict of lists CubeCombos, each keyed by a 2-tuple of Materials. TheoryR is the theoretical reflectance for each material.
    Returns extra reflectance for each material combo as well as the mean of all extra reflectances. This is what gets used. Ideally all the cubes will be very similar.
    Additionally returns a list of plot objects. references to these must be kept alive for the plots to be responsive."""
    rExtra = {}
    for matCombo, combosList in allCombos.items():
        print("Calculating rExtra for: ", matCombo)
        rExtra[matCombo] = {'combos': []}
        for combo in combosList:
            mat1, mat2 = combo.keys()
            _ = rExtra[matCombo]['combos']
            _.append(generateOneRExtraCube(combo, theoryR, correctErrors=True))
        rExtra[matCombo]['mean'] = reduce(lambda x, y: x + y, rExtra[matCombo]['combos']) / len(rExtra[matCombo]['combos'])
    _ = [rExtra[matCombo]['mean'] for matCombo in allCombos.keys()]
    rExtra['mean'] = reduce(lambda x, y: x + y, _) / len(_)
    plots = [PlotNd(rExtra[matCombo]['mean'], title=matCombo) for matCombo in allCombos.keys()] + [PlotNd(rExtra['mean'], title='Mean')]
    sampleCube: ImCube = list(allCombos.values())[0][0].data1
    erCube = ExtraReflectanceCube(rExtra['mean'], sampleCube.wavelengths, sampleCube.metadata)
    return erCube, rExtra, plots


def compareDates(cubes: pd.DataFrame) -> List[animation.ArtistAnimation]:
    anis = []
    mask = cubes['cube'].sample(n=1).iloc[0].selectLassoROI()
    for mat in set(cubes['material']):
        c = cubes[cubes['material'] == mat]
        fig, ax = plt.subplots()
        fig.suptitle(mat.name)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Counts/ms")
        fig2, ax2 = plt.subplots()
        fig2.suptitle(mat.name)
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
    return anis
