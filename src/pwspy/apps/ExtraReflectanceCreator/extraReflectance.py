from typing import Dict, List, Tuple, Iterable, Any, Sequence

from pwspy import ImCube, ExtraReflectanceCube
from pwspy.imCube.otherClasses import Roi
from pwspy.utility import reflectanceHelper
import itertools
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
import pandas as pd


def _interpolateNans(arr):
    def interp1(arr1):
        nans = np.isnan(arr1)
        f = lambda z: z.nonzero()[0]
        arr1[nans] = np.interp(f(nans), f(~nans), arr1[~nans])
        return arr1

    arr = np.apply_along_axis(interp1, 2, arr)
    return arr


def getTheoreticalReflectances(materials: Iterable[str], index: Tuple[float]) -> Dict:
    """Generate a dictionary containing a pandas series of the `material`-glass reflectance for each material in
    `materials`. Index is in units of nanometers."""
    theoryR = {}
    for material in materials:  # For each unique material in the `cubes` list
        theoryR[material] = reflectanceHelper.getReflectance(material, 'glass', index=index)
    return theoryR


def generateMaterialCombos(materials: Iterable[str], excludedCombos: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Given a list of material strings and a list of material combination tuples that should be skipped, this function returns
    a list of all possible material combo tuples"""
    matCombos = list(itertools.combinations(materials, 2))  # All the combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Remove excluded combinations.
    for i, (m1, m2) in enumerate(matCombos):  # Make sure to arrange materials so that our reflectance ratio is greater than 1
        if (reflectanceHelper.getReflectance(m1, 'glass') / reflectanceHelper.getReflectance(m2, 'glass')).mean() < 1:
            matCombos[i] = (m2, m1)
    return matCombos


def getAllCubeCombos(matCombos: Iterable[Tuple[str, str]], df: pd.DataFrame) -> Dict[Tuple[str, str], List[Dict[str, pd.DataFrame]]]:
    """Given a list of material combo tuples, return a dictionary whose keys are the material combo tuples and whose values are
    lists of Dicts containing a cube keyed by a material name. `cubes` is a list of the ImCubes to include in the output,
    each one must have a `material` attribute."""
    allCombos = {}
    for matCombo in matCombos:
        matCubes = {material: df[df['material'] == material] for material in matCombo}  # The imcubes relevant to this loop.
        allCombos[matCombo] = [dict(zip(matCubes.keys(), combo)) for combo in itertools.product(*matCubes.values())]
    return allCombos


def calculateSpectraFromCombos(cubeCombos: Dict[Tuple[str,str], Any], theoryR: dict, mask: Roi = None) -> Tuple[Dict, Dict]:
    """Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module and a
    `setting` property labeling how the microscope was set up for this image.

    This is used to examine the output of extra reflection calculation before using saveRExtra to save a cube for each setting.
    Returns a dictionary containing
    """

    allCombos = {}
    for matCombo, cubeCombos in cubeCombos.items():
        allCombos[matCombo] = [{'cubes': combo} for combo in cubeCombos]

    # Save the results of relevant calculations to a dictionary, this dictionary will be returned to the user along with
    # the raw data, `allCombos`
    meanValues = {}
    params = ['rextra', 'I0', 'mat1Spectra', 'mat2Spectra', 'cFactor']
    for matCombo in allCombos.keys():
        for combo in allCombos[matCombo]:
            cubes: Dict[str, ImCube] = combo['cubes']
            mat1, mat2 = cubes.keys()
            combo['mat1Spectra'] = cubes[mat1].getMeanSpectra(mask)[0]
            combo['mat2Spectra'] = cubes[mat2].getMeanSpectra(mask)[0]
            combo['rextra'] = ((theoryR[mat1] * combo['mat2Spectra']) - (theoryR[mat2] * combo['mat1Spectra'])) / (
                    combo['mat1Spectra'] - combo['mat2Spectra'])
            combo['I0'] = combo['mat2Spectra'] / (theoryR[mat2] + combo['rextra'])
            combo['cFactor'] = (combo['rextra'].mean() + theoryR['water'].mean()) / theoryR['water'].mean()
        meanValues[matCombo] = {
                param: np.array(list(
                        [combo[param] for combo in cubeCombos[matCombo]])).mean(axis=0) for param in params}
    meanValues['mean'] = {param: np.array(list([meanValues[matCombo][param] for matCombo in cubeCombos.keys()])).mean(axis=0) for param in params}
    return meanValues, allCombos


def prepareData(df: pd.DataFrame, selectMaskUsingSetting: str = None, excludedCombos: list = None) -> Tuple[Dict, Dict, Dict, List[Tuple[str, str]], Iterable]:
    # Error checking
    for col in ['cubes', 'material', 'setting']:
        assert col in df.columns

    if excludedCombos is None:
        excludedCombos = []
    settings = set(df['setting'])  # Unique setting values
    materials = set(df['material'])
    theoryR = getTheoreticalReflectances(materials, df['cubes'][0].wavelengths)  # Theoretical reflectances
    matCombos = generateMaterialCombos(materials, excludedCombos)

    if selectMaskUsingSetting is None:
        mask = df['cubes'][0]
    else:
        mask = df[df['setting'] == selectMaskUsingSetting]['cubes'][0]
    print("Select an ROI")
    mask = np.ones(df['cubes'][0].data.shape).astype(np.bool)# mask = mask.selectLassoROI()  # Select an ROI to analyze

    meanValues = {}
    allCombos = {}
    for sett in settings:
        cubeCombos = getAllCubeCombos(matCombos, df[df['setting'] == sett])
        meanValues[sett], allCombos[sett] = calculateSpectraFromCombos(cubeCombos, theoryR, mask)
    return meanValues, allCombos, theoryR, matCombos, settings

def plotExtraReflection(allCombos: Dict, meanValues: Dict, theoryR: dict, matCombos:List[Tuple[str,str]], settings:Iterable, plotReflectionImages: bool = False):
    fig, ax = plt.subplots()  # For extra reflections
    fig.suptitle("Extra Reflection")
    ax.set_ylabel("%")
    ax.set_xlabel("nm")
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo['cubes']
                ax.plot(cubes[mat1].wavelengths, combo['rextra'],
                        label=f'{sett} {mat1}:{int(cubes[mat1].exposure)}ms {mat2}:{int(cubes[mat2].exposure)}ms')
        ax.plot(cubes[mat1].wavelengths, meanValues[sett]['mean']['rextra'], color='k', label=f'{sett} mean')
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
                cubes = combo['cubes']
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, combo['mat1Spectra'] / combo['mat2Spectra'],
                                         label=f'{sett} {mat1}:{int(cubes[mat1].exposure)}ms {mat2}:{int(cubes[mat2].exposure)}ms')
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
        scatterPointsX = [((meanValues[sett][matCombo]['mat1Spectra'] - means['I0'] * means['rextra']) / (
                meanValues[sett][matCombo]['mat2Spectra'] - means['I0'] * means['rextra'])).mean() for matCombo in
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
                    cubes = combo['cubes']
                    plt.figure()
                    plt.title(f"Reflectance %. {sett}, {mat1}:{int(cubes[mat2].exposure)}ms, {mat2}:{int(cubes[mat2].exposure)}ms")
                _ = ((theoryR[mat1][np.newaxis, np.newaxis, :] * cubes[mat2].data) - (
                        theoryR[mat2][np.newaxis, np.newaxis, :] * cubes[mat1].data)) / (
                            cubes[mat1].data - cubes[mat2].data)
                _[np.isinf(_)] = np.nan
                if np.any(np.isnan(_)):
                    _ = _interpolateNans(   _)  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
                refIm = _.mean(axis=2)
                plt.imshow(refIm, vmin=np.percentile(refIm, .5), vmax=np.percentile(refIm, 99.5))
                plt.colorbar()

        print(f"{sett} correction factor")
        print(means['cFactor'])


def saveRExtra(allCombos: Dict, theoryR: dict, matCombos:List[Tuple[str,str]]) -> Dict[str, ExtraReflectanceCube]:
    """Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module."""

    rExtra = {}
    for matCombo in matCombos:
        print("Calculating rExtra for: ", matCombo)
        rExtra[matCombo] = {'combos': []}
        for combo in allCombos[matCombo]:
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
    _ = [rExtra[matCombo]['mean'] for matCombo in matCombos]
    rExtra['mean'] = reduce(lambda x, y: x + y, _) / len(_)
    return rExtra
