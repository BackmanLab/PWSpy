# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""A collection of functions dedicated to the purpose of generating Extra Reflectance calibrations from images of
materials with known reflectances (e.g. air/glass interface, water/glass interface.)
These functions are relied on heavily in the pwspy.apps.ERCreator app.

Functions
----------
.. autosummary::
   :toctree: generated/

   getTheoreticalReflectances
   generateMaterialCombos
   getAllCubeCombos
   plotExtraReflection
   generateRExtraCubes

Classes
--------
.. autosummary
   :toctree: generated/

   CubeCombo
"""
import logging
from typing import Dict, List, Tuple, Iterable, Any, Iterator, Union, Optional, Set
from pwspy.dataTypes import Roi, ExtraReflectanceCube, ImCube, ERMetaData
from pwspy.utility.reflection import reflectanceHelper, Material
import itertools
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
import pandas as pd
from dataclasses import dataclass
from matplotlib import animation
from mpl_qt_viz.visualizers import PlotNd


MCombo = Tuple[Material, Material]  # This is just an alias to shorten some of the type hinting.


class CubeCombo:
    """A convenient way of packaging together two ImCubes along with the material that each ImCube is an image of.

    Args:
        material1: The material that was imaged in `cube1`
        material2: The material that was imaged in `cube2`
        cube1: An ImCube with an image of a glass-{material} interface where the material is `material1`.
        cube2: An ImCube with an image of a glass-{material} interface where the material is `material2`.

    """
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
class _ComboSummary:
    """A convenient packaging of information related to the extra reflectance calculated from a single _CubeCombo"""
    mat1Spectra: np.ndarray
    mat2Spectra: np.ndarray
    combo: CubeCombo
    rExtra: np.ndarray
    I0: np.ndarray
    cFactor: float
    weight: np.ndarray


def _interpolateNans(arr):
    """Interpolate out nan values along the third axis of an array"""

    def interp1(arr1):
        nans = np.isnan(arr1)
        f = lambda z: z.nonzero()[0]
        arr1[nans] = np.interp(f(nans), f(~nans), arr1[~nans])
        return arr1

    arr = np.apply_along_axis(interp1, 2, arr)
    return arr


def getTheoreticalReflectances(materials: Set[Material], wavelengths: Tuple[float], numericalAperture: float) -> Dict[Material, pd.Series]:
    """Generate a dictionary containing a pandas series of the `material`-glass reflectance for each material in
    `materials`.

    Args:
        materials: The set of materials that you want to retrieve the theoretical reflectance for.
        wavelengths: The wavelengths that you want the reflectances calculated at.
        numericalAperture: The numerical aperture that the reflectance should be calculated at.

    Returns:
        A dictionary of the reflectances for each material.
    """

    theoryR = {}
    for material in materials:  # For each unique material in the `cubes` list
        logging.getLogger(__name__).info(f"Calculating reflectance for {material}")
        theoryR[material] = reflectanceHelper.getReflectance(material, Material.Glass, wavelengths=wavelengths, NA=numericalAperture)
    return theoryR


def generateMaterialCombos(materials: Iterable[Material], excludedCombos: Optional[Iterable[MCombo]] = None) -> List[MCombo]:
    """Given a list of materials, this function returns a list of all possible material combo tuples.

    Args:
        materials: The list of materials that you want to generate every possible combo of.
        excludedCombos: Combinations of materials that you don't want included in the combinations.

    Returns:
        A list of Material combinations.

    """
    if excludedCombos is None:
        excludedCombos = []
    matCombos = list(itertools.combinations(materials, 2))  # All the combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Remove excluded combinations.
    for i, (m1, m2) in enumerate(matCombos):  # Make sure to arrange materials so that our reflectance ratio is greater than 1
        if (reflectanceHelper.getReflectance(m1, Material.Glass) / reflectanceHelper.getReflectance(m2, Material.Glass)).mean() < 1:
            matCombos[i] = (m2, m1)
    return matCombos


def getAllCubeCombos(matCombos: Iterable[MCombo], df: pd.DataFrame) -> Dict[MCombo, List[CubeCombo]]:
    """Given a list of material combo tuples, return a dictionary whose keys are the material combo tuples and whose values are
    lists of CubeCombos.

    Args:
        matCombos: A list of material combinations, most likely generated by `generateMaterialCombos`
        df: A Pandas DataFrame containing a 'material' column of the materials, and a 'cube' column containing the associated ImCube

    Returns:
        A dictionary with a key for each material combination. Each value is a list of all the `CubeCombo`s extracted from `df`.
    """
    allCombos = {}
    for matCombo in matCombos:
        matCubes = {material: df[df['material'] == material]['cube'] for material in matCombo}  # A dictionary sorted by material containing lists of the ImCubes that are relevant to this loop..
        allCombos[matCombo] = [CubeCombo(*matCubes.keys(), *combo) for combo in itertools.product(*matCubes.values())]
    allCombos = {key: val for key, val in allCombos.items() if len(val) > 0}  # In some cases a matCombo appears for which there is no data. get rid of these.
    return allCombos


def _calculateSpectraFromCombos(cubeCombos: Dict[MCombo, List[CubeCombo]], theoryR: Dict[Material, pd.Series],
                                numericalAperture: float, mask: Optional[Roi] = None) ->\
        Tuple[Dict[Union[MCombo, str], Dict[str, Any]], Dict[MCombo, List[_ComboSummary]]]:
    """This is used to examine the output of extra reflection calculation before using saveRExtra to save a cube for each setting.
    Expects a dictionary as created by `getAllCubeCombos` and a dictionary of theoretical reflections.

    Args:
        cubeCombos: A dictionary containing all possible combinations of ImCubes measured at different materials. Keyed by the material combo.
        theoryR: A dictionary containing the theoretical reflectances for all `Materials` in use. Should be accurate for the `numericalAperture` in question.
        numericalAperture: The illumination numerial aperture that the images were taken at.
        mask: An ROI that limits the region of the ImCubes that is analyzed. The spectra will be averaged over this region. If `None` the spectra will be average over the full XY FOV.

    Returns:
        The first item is a dictionary containing information about the average calculation for each material combination
        as well as the average calculation accross all material combinations. The seconds item is a dictionary containing
        information about every single cube combo.
    """

    # Save the results of relevant calculations to a dictionary, this dictionary will be returned to the user along with
    # the raw data, `allCombos`
    allCombos = {}
    meanValues = {}
    params = ['rExtra', 'I0', 'mat1Spectra', 'mat2Spectra']
    for matCombo in cubeCombos.keys():
        allCombos[matCombo] = []
        for combo in cubeCombos[matCombo]:
            mat1, mat2 = combo.keys()
            c = _ComboSummary(mat1Spectra=combo[mat1].getMeanSpectra(mask)[0],
                              mat2Spectra=combo[mat2].getMeanSpectra(mask)[0],
                              weight=None,
                              rExtra=None,
                              I0=None,
                              cFactor=None,
                              combo=combo)
            c.weight = (c.mat1Spectra - c.mat2Spectra) ** 2 / (c.mat1Spectra ** 2 + c.mat2Spectra ** 2)
            c.rExtra = ((theoryR[mat1] * c.mat2Spectra) - (theoryR[mat2] * c.mat1Spectra)) / (c.mat1Spectra - c.mat2Spectra)
            c.I0 = c.mat2Spectra / (theoryR[mat2] + c.rExtra)
            waterTheory = reflectanceHelper.getReflectance(Material.Water, Material.Glass, wavelengths=list(theoryR.values())[0].index, NA=numericalAperture)
            c.cFactor = (c.rExtra.mean() + waterTheory.mean()) / waterTheory.mean()
            allCombos[matCombo].append(c)
        meanValues[matCombo] = {}
        for param in params:
            meanValues[matCombo][param] = np.average(np.array(list([getattr(combo, param) for combo in allCombos[matCombo]])),
                                                    axis=0,
                                                    weights=np.array([combo.weight for combo in allCombos[matCombo]]))
        meanValues[matCombo]['cFactor'] = np.average(np.array([combo.cFactor for combo in allCombos[matCombo]]),
                                                     axis=0,
                                                     weights=np.array([combo.weight.mean() for combo in allCombos[matCombo]]))
        meanValues[matCombo]['weight'] = np.mean(np.array([combo.weight for combo in allCombos[matCombo]]))
    meanValues['mean'] = {param: np.average(np.array(list([meanValues[matCombo][param] for matCombo in cubeCombos.keys()])),
                                            axis=0,
                                            weights=np.array([meanValues[matCombo]['weight'] for matCombo in cubeCombos.keys()])) for param in params}
    meanValues['mean']['cFactor'] = np.average(np.array([meanValues[matCombo]['cFactor'] for matCombo in cubeCombos.keys()]),
                                                 axis=0,
                                                 weights=np.array([meanValues[matCombo]['weight'].mean() for matCombo in cubeCombos.keys()]))
    return meanValues, allCombos


def plotExtraReflection(df: pd.DataFrame, theoryR: Dict[Material, pd.Series], matCombos: List[MCombo],
                        numericalAperture: float, mask: Optional[Roi] = None,
                        plotReflectionImages: bool = False) -> List[plt.Figure]:
    """Generate a variety of plots displaying information about the extra reflectance calculation.
    
    Args:
        df: A pandas dataframe containging a row for each ImCube that is to be included in the calculation. The dataframe
            should have the following columns: 'cube': The `ImCube` object in question, should be an image of a
            glass-{material} interface. `material`: The `Material` that the ImCube is an image of. `setting`: A string
            describing the imaging configuration. If the dataframe has multiple settings then each settings will be
            processed separately and compared.
        theoryR: A dictionary where the key is a `Material` and the value is a pandas series giving the reflectance for
            a glass-{material} reflection over a range of wavelengths. The index of the series should be the wavelengths.
        matCombos: A list of the various material combinations that should be evaluated.
        numericalAperture: The numerical aperture that the ImCubes being used were imaged at.
        mask: An ROI indicating the region of the images that should be included in the evaluation.
        plotReflectionImages: An optional parameter. If True additional plots will be opened.

    Returns:
        A list of matplotlib figures resulting from this calculation.

    """
    settings = set(df['setting'])
    meanValues: Dict[str, Dict[Union[MCombo, str], Dict[str, Any]]] = {}
    allCombos: Dict[str, Dict[MCombo, List[_ComboSummary]]] = {}
    for sett in settings:
        cubeCombos = getAllCubeCombos(matCombos, df[df['setting'] == sett])
        meanValues[sett], allCombos[sett] = _calculateSpectraFromCombos(cubeCombos, theoryR, numericalAperture, mask)
    figs = []
    fig, ax = plt.subplots()  # For extra reflections
    fig.suptitle("Extra Reflection")
    figs.append(fig)
    ax.set_ylabel("Reflectance (1 = total reflection)")
    ax.set_xlabel("nm")
    i = 0
    numLines = []
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            numLines.append(len(allCombos[sett][matCombo]))
    numLines = sum(numLines)
    colormap = plt.cm.gist_rainbow
    colors = [colormap(i) for i in np.linspace(0, 0.99, numLines)]
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo.combo
                ax.plot(cubes[mat1].wavelengths, combo.rExtra, color=colors[i],
                        label=f'{sett} {mat1}:{int(cubes[mat1].metadata.exposure)}ms {mat2}:{int(cubes[mat2].metadata.exposure)}ms')
                i += 1
        ax.plot(cubes[mat1].wavelengths, meanValues[sett]['mean']['rExtra'], color='k', label=f'{sett} mean')  # TODO Add a hover annotation since all of the lines are black it's impossible to know which one is which.
    ax.legend()

    fig2, ratioAxes = plt.subplots(nrows=len(matCombos))  # for correction factor
    figs.append(fig2)
    if not isinstance(ratioAxes, np.ndarray): ratioAxes = np.array(ratioAxes).reshape(1)  # If there is only one axis we still want it to be a list for the rest of the code
    ratioAxes = dict(zip(matCombos, ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0].name}/{combo[1].name} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]] / theoryR[combo[1]], label='Theory')
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo.combo
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, combo.mat1Spectra / combo.mat2Spectra,
                                         label=f'{sett} {mat1.name}:{int(cubes[mat1].metadata.exposure)}ms {mat2.name}:{int(cubes[mat2].metadata.exposure)}ms')
    [ratioAxes[combo].legend() for combo in matCombos]

    for sett in settings:
        settMatCombos = allCombos[sett].keys()  # Sometime we are looking at settings which don't have all the same matCombos. Only use the combos specific to this setting.
        means = meanValues[sett]['mean']
        fig6, scatterAx3 = plt.subplots()
        fig6.suptitle(f'{sett}')
        figs.append(fig6)
        scatterAx3.set_ylabel("Theoretical Ratio")
        scatterAx3.set_xlabel("Observed Ratio. No correction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in settMatCombos]
        scatterPointsX = [(meanValues[sett][matCombo]['mat1Spectra'] / meanValues[sett][matCombo]['mat2Spectra']).mean() for
                          matCombo in settMatCombos]
        [scatterAx3.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in zip(scatterPointsX, scatterPointsY, settMatCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx3.plot(x, x, label='1:1')
        scatterAx3.legend()

        fig3, scatterAx = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        fig3.suptitle(f'{sett} cFactor: {means["cFactor"]}')
        figs.append(fig3)
        scatterAx.set_ylabel("Theoretical Ratio")
        scatterAx.set_xlabel("Observed Ratio w/ cFactor")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in settMatCombos]
        scatterPointsX = [means['cFactor'] * (
                meanValues[sett][matCombo]['mat1Spectra'] / meanValues[sett][matCombo]['mat2Spectra']).mean() for
                          matCombo in settMatCombos]
        [scatterAx.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in zip(scatterPointsX, scatterPointsY, settMatCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx.plot(x, x, label='1:1')
        scatterAx.legend()

        fig4, scatterAx2 = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        fig4.suptitle(sett)
        figs.append(fig4)
        scatterAx2.set_ylabel("Theoretical Ratio")
        scatterAx2.set_xlabel("Observed Ratio after Subtraction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in settMatCombos]
        scatterPointsX = [((meanValues[sett][matCombo]['mat1Spectra'] - means['I0'] * means['rExtra']) / (
                meanValues[sett][matCombo]['mat2Spectra'] - means['I0'] * means['rExtra'])).mean() for matCombo in
                          settMatCombos]
        [scatterAx2.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, settMatCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx2.plot(x, x, label='1:1')
        scatterAx2.legend()

        if plotReflectionImages:
            for matCombo in settMatCombos:
                mat1, mat2 = matCombo
                for combo in allCombos[sett][matCombo]:
                    cubes = combo.combo
                    fig5 = plt.figure()
                    figs.append(fig5)
                    plt.title(f"Reflectance %. {sett}, {mat1}:{int(cubes[mat1].metadata.exposure)}ms, {mat2}:{int(cubes[mat2].metadata.exposure)}ms")
                    _ = ((theoryR[mat1][np.newaxis, np.newaxis, :] * cubes[mat2].data) - (
                        theoryR[mat2][np.newaxis, np.newaxis, :] * cubes[mat1].data)) / (
                            cubes[mat1].data - cubes[mat2].data)
                    _[np.isinf(_)] = np.nan
                    if np.any(np.isnan(_)):
                        _ = _interpolateNans(_)  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
                    refIm = _.mean(axis=2)
                    plt.imshow(refIm, vmin=np.percentile(refIm, .5), vmax=np.percentile(refIm, 99.5))
                    plt.colorbar()

        logging.getLogger(__name__).info(f"{sett} correction factor")
    return figs


def _generateOneRExtraCube(combo: CubeCombo, theoryR: Dict[Material, pd.Series]) -> Tuple[np.ndarray, np.ndarray]:
    """Given a combination of two ImCubes imaging different materials and the theoretical reflectance for the materials
    imaged in the two ImCubes this function will generate an estimation of the extra reflectance in the system.

    Args:
        combo: A combo of two ImCubes imaging two different glass-material interfaces.
        theoryR: A dictionary providing pandas series giving the theoretically expected reflectance for each glass-material
            interface represented by the two ImCubes.

    Returns:
        The first item is the array of the estimated extra reflectance of the system, expressed as values between 0 and
        1 (this is the same shape as the ImCubes supplied to the function.) The second item is an estimate of how reliable
        each element in the array is.

    """
    data1 = combo.data1.data
    data2 = combo.data2.data
    T1 = np.array(theoryR[combo.mat1][np.newaxis, np.newaxis, :])
    T2 = np.array(theoryR[combo.mat2][np.newaxis, np.newaxis, :])
    denominator = data1 - data2
    nominator = T1 * data2 - T2 * data1
    arr = nominator / denominator

    #Even when a weight is calculated as zero if we have weird values (np.nan, np.inf) in arr we will get a messed up end result.
    arr[np.isinf(arr)] = 0
    arr[np.isnan(arr)] = 0
    arr[arr < 0] = 0
    arr[arr > 1] = 1
    #calculate a confidence weighting for every point in the cube.
    # According to propagation of error if we assume that TheoryR has no error
    # and the data (camera counts) has a constant error of C then the error is C * sqrt((T1-T2)*data1^2 + (T2-T1)*data2^2) / (data1 - data2)^2
    # Since we are just looking for a relative measure of confidence we can ignore C. We use the `Variance weighted average'
    # (1/stddev^2)
    #Doing this calculation with noise in Theory instead of data gives us a variance of C^2 * (data1^2 + data2^2) / (data1 - data2)^2. this seems like a better equation to use. TODO Really? Why?
    weight = (data1-data2)**2 / (data1**2 + data2**2) # The weight is the inverse of the variance. Higher weight = more reliable data.
    return arr, weight


def generateRExtraCubes(allCombos: Dict[MCombo, List[CubeCombo]], theoryR: dict, numericalAperture: float) -> \
        Tuple[ExtraReflectanceCube, Dict[Union[str, MCombo], Tuple[np.ndarray, np.ndarray]], List[PlotNd]]:
    """Generate a series of extra reflectance cubes based on the input data.

    Args:
        allCombos: a dict of lists CubeCombos, each keyed by a 2-tuple of Materials.
        theoryR: the theoretical reflectance for each material.
        numericalAperture: The numerical aperture that the ImCubes were imaged at. The theoryR reflectances should have
            also been calculated at this NA

    Returns:
        Returns extra reflectance for each material combo as well as the mean of all extra reflectances.
        This is what gets used. Ideally all the cubes will be very similar.
        Additionally returns a list of plot objects. references to these must be kept alive for the plots to be responsive.
    """
    rExtra = {}
    for matCombo, combosList in allCombos.items():
        logging.getLogger(__name__).info(f"Calculating rExtra for: {matCombo}")
        erCubes, weights = zip(*[_generateOneRExtraCube(combo, theoryR) for combo in combosList])
        weightSum = reduce(lambda x,y: x+y, weights)
        weightedMean = reduce(lambda x,y: x+y, [cube*weight for cube, weight in zip(erCubes, weights)]) / weightSum
        meanWeight = weightSum / len(weights)
        rExtra[matCombo] = (weightedMean, meanWeight)
    erCubes, weights = zip(*rExtra.values())
    weightSum = reduce(lambda x, y: x + y, weights)
    weightedMean = reduce(lambda x, y: x + y, [cube * weight for cube, weight in zip(erCubes, weights)]) / weightSum
    meanWeight = weightSum / len(weights)
    rExtra['mean'] = (weightedMean, meanWeight)
    sampleCube: ImCube = list(allCombos.values())[0][0].data1
    plots = [PlotNd(rExtra[k][0], title=k, indices=[range(sampleCube.data.shape[0]), range(sampleCube.data.shape[1]), sampleCube.wavelengths]) for k in rExtra.keys()]
    md = ERMetaData(sampleCube.metadata.dict, numericalAperture)
    erCube = ExtraReflectanceCube(rExtra['mean'][0], sampleCube.wavelengths, md)
    return erCube, rExtra, plots



