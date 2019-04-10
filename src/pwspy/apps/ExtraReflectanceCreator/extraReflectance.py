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

MCombo = Tuple[Material, Material]

class CubeCombo:
    def __init__(self, material1: Material, material2: Material, cube1: pd.DataFrame, cube2: pd):
        self.mat1 = material1
        self.mat2 = material2
        self.data1 = cube1
        self.data2 = cube2

    def keys(self) -> MCombo:
        return (self.mat1, self.mat2)

    def values(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        return (self.data1, self.data2)

    def items(self) -> Iterator[Tuple[Material, pd.DataFrame]]:
        return zip(self.keys(), self.values())

    def __getitem__(self, item: Material) -> pd.DataFrame:
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


def calculateSpectraFromCombos(cubeCombos: Dict[MCombo, List[CubeCombo]], theoryR: dict, mask: Roi = None) -> Tuple[Dict[Union[MCombo, str], Dict[str, Any]], Dict[MCombo, List[ComboSummary]]]:
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


def prepareData(df: pd.DataFrame, settings: Iterable[str], matCombos: Iterable[MCombo], theoryR: Dict[Material, pd.Series], mask: Optional[Roi] = None) -> Tuple[Dict[str, Dict[Union[MCombo, str], Dict[str, Any]]],
                                                                                                            Dict[str, Dict[MCombo, List[ComboSummary]]]]:
    meanValues = {}
    allCombos = {}
    for sett in settings:
        cubeCombos = getAllCubeCombos(matCombos, df[df['setting'] == sett])
        meanValues[sett], allCombos[sett] = calculateSpectraFromCombos(cubeCombos, theoryR, mask)
    return meanValues, allCombos


def plotExtraReflection(allCombos: Dict[str, Dict[MCombo, List[ComboSummary]]], meanValues: Dict, theoryR: dict, matCombos:List[MCombo], settings:Iterable, plotReflectionImages: bool = False):
    fig, ax = plt.subplots()  # For extra reflections
    fig.suptitle("Extra Reflection")
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
    if not isinstance(ratioAxes, np.ndarray): ratioAxes = np.array(ratioAxes).reshape(
        1)  # If there is only one axis we still want it to be a list for the rest of the code
    ratioAxes = dict(zip(matCombos, ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0]}/{combo[1]} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]] / theoryR[combo[1]], label='Theory')
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo.combo
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, combo.mat1Spectra / combo.mat2Spectra,
                                         label=f'{sett} {mat1}:{int(cubes[mat1].metadata["exposure"])}ms {mat2}:{int(cubes[mat2].metadata["exposure"])}ms')
    [ratioAxes[combo].legend() for combo in matCombos]

    for sett in settings:
        means = meanValues[sett]['mean']

        fig3, scatterAx = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        scatterAx.set_ylabel("Theoretical Ratio")
        scatterAx.set_xlabel("Observed Ratio w/ cFactor")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [means['cFactor'] * (
                meanValues[sett][matCombo]['mat1Spectra'] / meanValues[sett][matCombo]['mat2Spectra']).mean() for
                          matCombo in matCombos]
        [scatterAx.scatter(x, y, label=f'{matCombo[0]}/{matCombo[1]}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx.plot(x, x, label='1:1')
        scatterAx.legend()

        fig4, scatterAx2 = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        scatterAx2.set_ylabel("Theoretical Ratio")
        scatterAx2.set_xlabel("Observed Ratio after Subtraction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [((meanValues[sett][matCombo]['mat1Spectra'] - means['I0'] * means['rExtra']) / (
                meanValues[sett][matCombo]['mat2Spectra'] - means['I0'] * means['rExtra'])).mean() for matCombo in
                          matCombos]
        [scatterAx2.scatter(x, y, label=f'{matCombo[0]}/{matCombo[1]}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx2.plot(x, x, label='1:1')
        scatterAx2.legend()

        if plotReflectionImages:
            for matCombo in matCombos:
                mat1, mat2 = matCombo
                for combo in allCombos[sett][matCombo]:
                    cubes = combo.combo
                    plt.figure()
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


def saveRExtra(allCombos: Dict[MCombo, Dict], theoryR: dict) -> Dict[str, ExtraReflectanceCube]:
    """No longer true: Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module."""

    rExtra = {}
    for matCombo, combosList in allCombos.items():
        print("Calculating rExtra for: ", matCombo)
        rExtra[matCombo] = {'combos': []}
        for combo in combosList:
            combo = combo.combo #Just select out the imcube data
            mat1, mat2 = combo.keys()
            _ = rExtra[matCombo]['combos']
            _.append(((np.array(theoryR[mat1][np.newaxis, np.newaxis, :]) * combo[mat2].data) - (
                    np.array(theoryR[mat2][np.newaxis, np.newaxis, :]) * combo[mat1].data)) / (
                                       combo[mat1].data - combo[mat2].data))
            _[-1][np.isinf(_[-1])] = np.nan
            nans = np.isnan(_[-1]).sum()
            if nans > 0:
                print(nans, " invalid values detected in " + str(matCombo) + ". Interpolating.")
                _[-1] = _interpolateNans(_[-1])  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
        rExtra[matCombo]['mean'] = reduce(lambda x, y: x + y, rExtra[matCombo]['combos']) / len(rExtra[matCombo]['combos'])
    _ = [rExtra[matCombo]['mean'] for matCombo in allCombos.keys()]
    rExtra['mean'] = reduce(lambda x, y: x + y, _) / len(_)
    return rExtra


