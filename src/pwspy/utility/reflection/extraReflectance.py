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

"""
A collection of functions dedicated to the purpose of generating Extra Reflectance calibrations from images of
materials with known reflectances (e.g. air/glass interface, water/glass interface.)

By calculating the "extra reflectance" of a microscope system we can come up with a subtraction from our raw data that
will make our ratiometric measurements proportional to the actual sample reflectance.

These functions are relied on heavily in "ERCreator" app found in `pwspy_gui.ExtraReflectanceCreator`.

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
import typing as t_

import pwspy.dataTypes as pwsdt
from pwspy.utility.reflection import reflectanceHelper, Material
import itertools
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
import pandas as pd
from dataclasses import dataclass
import matplotlib as mpl
__all__ = ['getAllCubeCombos', 'generateMaterialCombos', 'generateRExtraCubes', 'getTheoreticalReflectances']

MCombo = t_.Tuple[Material, Material]  # This is just an alias to shorten some of the type hinting.


class CubeCombo:
    """A convenient way of packaging together two PwsCubes along with the material that each PwsCube is an image of.

    Args:
        material1: The material that was imaged in `cube1`
        material2: The material that was imaged in `cube2`
        cube1: An PwsCube with an image of a glass-{material} interface where the material is `material1`.
        cube2: An PwsCube with an image of a glass-{material} interface where the material is `material2`.

    """
    def __init__(self, material1: Material, material2: Material, cube1: pwsdt.PwsCube, cube2: pwsdt.PwsCube):
        self.mat1 = material1
        self.mat2 = material2
        self.data1 = cube1
        self.data2 = cube2

    def keys(self) -> MCombo:
        return self.mat1, self.mat2

    def values(self) -> t_.Tuple[pwsdt.PwsCube, pwsdt.PwsCube]:
        return self.data1, self.data2

    def items(self) -> t_.Iterator[t_.Tuple[Material, pwsdt.PwsCube]]:
        return zip(self.keys(), self.values())

    def __getitem__(self, item: Material) -> pwsdt.PwsCube:
        """cubeCombo[myMaterial] will return the data class for that material."""
        if item == self.mat1:
            return self.data1
        elif item == self.mat2:
            return self.data2
        else:
            raise KeyError("Key must be either mat1 or mat2.")


@dataclass
class _ComboSummary:
    """A convenient packaging of information related to the extra reflectance calculated from a single _CubeCombo"""
    mat1Spectra: np.ndarray  # The average spectrum in the ROI
    mat2Spectra: np.ndarray
    rExtra: np.ndarray
    I0: np.ndarray
    weight: np.ndarray


def getTheoreticalReflectances(materials: t_.Set[Material], wavelengths: t_.Tuple[float], numericalAperture: float) -> t_.Dict[Material, pd.Series]:
    """Generate a dictionary containing a Pandas `Series` of the `material`-glass reflectance for each material in
    `materials`.

    Args:
        materials: The set of materials that you want to retrieve the theoretical reflectance for.
        wavelengths: The wavelengths that you want the reflectances calculated at.
        numericalAperture: The numerical aperture that the reflectance should be calculated at.

    Returns:
        A dictionary of the reflectances for each material. The material serves as the dictionary key.
    """
    theoryR = {}
    for material in materials:  # For each unique material
        logging.getLogger(__name__).info(f"Calculating reflectance for {material}")
        theoryR[material] = reflectanceHelper.getReflectance(material, Material.Glass, wavelengths=wavelengths, NA=numericalAperture)
    return theoryR


def generateMaterialCombos(materials: t_.Iterable[Material], excludedCombos: t_.Optional[t_.Iterable[MCombo]] = None) -> t_.List[MCombo]:
    """Given a list of materials, this function returns a list of all possible material combo tuples.

    Args:
        materials: The list of materials that you want to generate every possible combo of.
        excludedCombos: Combinations of materials that you don't want included in the combinations.

    Returns:
        A list of Material combinations.
    """
    if excludedCombos is None:
        excludedCombos = []
    matCombos = list(itertools.combinations(materials, 2))  # All the 2-combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Filter out all excluded combinations.
    for i, (m1, m2) in enumerate(matCombos):  # Make sure to arrange materials so that our reflectance ratio is greater than 1
        if (reflectanceHelper.getReflectance(m1, Material.Glass) / reflectanceHelper.getReflectance(m2, Material.Glass)).mean() < 1:
            matCombos[i] = (m2, m1)  # Swap elements if the ratio of reflectance is <1
    return matCombos


def getAllCubeCombos(matCombos: t_.Iterable[MCombo], cubeDict: t_.Dict[Material, t_.List[pwsdt.PwsCube]]) -> t_.Dict[MCombo, t_.List[CubeCombo]]:
    """Given a list of material combo tuples, return a dictionary whose keys are the material combo tuples and whose values are
    lists of CubeCombos.

    Args:
        matCombos: A list of material combinations, most likely generated by `generateMaterialCombos`
        cubeDict: An dictionary containing lists of a PwsCube measuremnts keyed by the material they were measured at.

    Returns:
        A dictionary with a key for each material combination. Each value is a list of all the `CubeCombo`s extracted from `cubes`.
    """
    allCombos = {}  # A dictionary where each key is a material combo, e.g. (mat1, mat2). The values are lists of every possible 2-combination of PwsCube measuremens for that material combo.
    for matCombo in matCombos:
        # Very important that The CubeCombo has data in the same order that the matCombo is in. Otherwise our data is all mismatched.
        matCubes = (
            cubeDict[matCombo[0]],
            cubeDict[matCombo[1]]
        )
        allCombos[matCombo] = [CubeCombo(*matCombo, *combo) for combo in itertools.product(*matCubes)]
    allCombos = {key: val for key, val in allCombos.items() if len(val) > 0}  # In some cases a matCombo appears for which there is no data. get rid of these.
    return allCombos


def _calculateSpectraFromCombos(cubeCombos: t_.Dict[MCombo, t_.List[CubeCombo]], theoryR: t_.Dict[Material, pd.Series],
                                 mask: t_.Optional[pwsdt.Roi] = None) ->\
        t_.Tuple[
            _ComboSummary,
            t_.Dict[MCombo, _ComboSummary],
            t_.Dict[MCombo, t_.List[t_.Tuple[_ComboSummary, CubeCombo]]]
        ]:
    """This is used to examine the output of extra reflection calculation before using saveRExtra to save a cube for each setting.
    Expects a dictionary as created by `getAllCubeCombos` and a dictionary of theoretical reflections.

    Args:
        cubeCombos: A dictionary containing all possible combinations of PwsCubes measured at different materials. Keyed by the material combo.
        theoryR: A dictionary containing the theoretical reflectances for all `Materials` in use. Should be accurate for the `numericalAperture` in question.
        mask: An ROI that limits the region of the PwsCubes that is analyzed. The spectra will be averaged over this region. If `None` the spectra will be average over the full XY FOV.

    Returns:
        The first item is a dictionary containing information about the average calculation for each material combination
        as well as the average calculation accross all material combinations. The seconds item is a dictionary containing
        information about every single cube combo.
    """
    # Generate summaries for every possible combination of measurements.
    allComboSummary: t_.Dict[MCombo, t_.List[t_.Tuple[_ComboSummary, CubeCombo]]] = {}  # Organize combos by the material combo they go with.
    for matCombo in cubeCombos.keys():
        allComboSummary[matCombo] = []
        for combo in cubeCombos[matCombo]:
            mat1, mat2 = combo.keys()
            spectra1 = combo[mat1].getMeanSpectra(mask)[0]
            spectra2 = combo[mat2].getMeanSpectra(mask)[0]
            weight = (spectra1 - spectra2) ** 2 / (spectra1 ** 2 + spectra2 ** 2) # See `_generateOneRExtraCube` for an explanation of this weighting.
            rExtra = ((theoryR[mat1] * spectra2) - (theoryR[mat2] * spectra1)) / (spectra1 - spectra2)
            I0 = spectra2 / (theoryR[mat2] + rExtra)  # Reconstructed intensity of illumination in same units as `spectra`. This could just as easily be done with material1. They are identical by definition.
            c = _ComboSummary(mat1Spectra=spectra1,
                              mat2Spectra=spectra2,
                              weight=weight,
                              rExtra=rExtra,
                              I0=I0)
            allComboSummary[matCombo].append((c, combo))

    # Calculate the averages for each material combo.
    meanComboSummary: t_.Dict[MCombo, t_.Any] = {}
    params = ('rExtra', 'I0', 'mat1Spectra', 'mat2Spectra')  # attribute names of _CubeCombo that are 1d arrays. Used for looping through and generating averages.
    for matCombo, comboSummaries in allComboSummary.items():
        weights = np.array([comboSummary.weight for comboSummary, _ in comboSummaries])
        spectra1 = np.average(np.array([comboSummary.mat1Spectra for comboSummary, _ in comboSummaries]), axis=0, weights=weights)
        spectra2 = np.average(np.array([comboSummary.mat2Spectra for comboSummary, _ in comboSummaries]), axis=0, weights=weights)
        I0 = np.average(np.array([comboSummary.I0 for comboSummary, _ in comboSummaries]), axis=0, weights=weights)
        rExtra = np.average(np.array([comboSummary.rExtra for comboSummary, _ in comboSummaries]), axis=0, weights=weights)
        meanSummary = _ComboSummary(
            mat1Spectra=spectra1,
            mat2Spectra=spectra2,
            weight=np.mean(weights, axis=0),
            rExtra=rExtra,
            I0=I0
        )
        meanComboSummary[matCombo] = meanSummary

    # Calculate the average accross all material combos.
    weights = np.array([comboSummary.weight for comboSummary in meanComboSummary.values()])
    totalMean = _ComboSummary(
        mat1Spectra=np.average(np.array([comboSummary.mat1Spectra for comboSummary in meanComboSummary.values()]), axis=0, weights=weights),
        mat2Spectra=np.average(np.array([comboSummary.mat2Spectra for comboSummary in meanComboSummary.values()]), axis=0, weights=weights),
        weight=np.mean(weights, axis=0),
        rExtra=np.average(np.array([comboSummary.rExtra for comboSummary in meanComboSummary.values()]), axis=0, weights=weights),
        I0=np.average(np.array([comboSummary.I0 for comboSummary in meanComboSummary.values()]), axis=0, weights=weights)
    )
    return totalMean, meanComboSummary, allComboSummary


def plotExtraReflection(images: t_.Dict[str, t_.Dict[Material, t_.List[pwsdt.PwsCube]]], theoryR: t_.Dict[Material, pd.Series], matCombos: t_.List[MCombo],
                        mask: t_.Optional[pwsdt.Roi] = None) -> t_.List[plt.Figure]:
    """Generate a variety of plots displaying information about the extra reflectance calculation.
    
    Args:
        images: A dictionary where the keys are strings representing some configuration of the system and the
            values are dictionaries where the keys are a `Material` and the values are lists of the `PwsCube` that were
            measured at the corresponding glass-{material} interface and configuration indicated by the dictionary keys.
        theoryR: A dictionary where the key is a `Material` and the value is a Pandas 'Series' giving the reflectance for
            a glass-{material} reflection over a range of wavelengths. The index of the series should be the wavelengths.
        matCombos: A list of the various material combinations that should be evaluated.
        mask: An ROI indicating the region of the images that should be included in the evaluation.

    Returns:
        A list of matplotlib figures resulting from this calculation.

    """
    from mpl_qt_viz.visualizers import DockablePlotWindow  # This is not a dependency of the library, just needed for this method.

    settings = set(images.keys())
    totalMean: t_.Dict[str, _ComboSummary] = {}
    meanValues: t_.Dict[str, t_.Dict[MCombo, _ComboSummary]] = {}
    allCombos: t_.Dict[str, t_.Dict[MCombo, t_.List[t_.Tuple[_ComboSummary, CubeCombo]]]] = {}
    for setting, materialCubeDict in images.items():
        cubeCombos = getAllCubeCombos(matCombos, materialCubeDict)
        totalMean[setting], meanValues[setting], allCombos[setting] = _calculateSpectraFromCombos(cubeCombos, theoryR, mask)

    dock = DockablePlotWindow("Primary")
    figs = [dock]
    fig, ax = dock.subplots("System Reflectance")  # For extra reflections
    ax.set_ylabel("System Reflectance % (100 = total reflection)")
    ax.set_xlabel("Wavelength (nm)")
    numLines = []
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            numLines.append(len(allCombos[sett][matCombo]))
    numLines = sum(numLines)
    colormap = plt.cm.gist_rainbow
    colorCycle = mpl.cycler(color=plt.cm.gist_rainbow(np.linspace(0, 0.99, numLines)))
    ax.set_prop_cycle(colorCycle)
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            mat1, mat2 = matCombo
            for comboSummary, combo in allCombos[sett][matCombo]:
                cubes = combo
                ax.plot(cubes[mat1].wavelengths, comboSummary.rExtra * 100,
                        label=f'{sett} {mat1.name} : {mat2.name}')
        ax.plot(cubes[mat1].wavelengths, totalMean[sett].rExtra * 100, color='k', label=f'{sett} Weighted Avg.')  # TODO Add a hover annotation since all of the lines are black it's impossible to know which one is which.
    ax.legend()

    fig2, ratioAxes = dock.subplots("Reflectance Ratios",
                                    subplots_kwargs=dict(nrows=len(matCombos))
                                    )  # for correction factor
    if not isinstance(ratioAxes, np.ndarray):
        ratioAxes = np.array(ratioAxes).reshape(1)  # If there is only one axis we still want it to be a list for the rest of the code
    ratioAxes = dict(zip(matCombos, ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0].name}/{combo[1].name} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]] / theoryR[combo[1]], label='Theory')
    for sett in settings:
        for matCombo in allCombos[sett].keys():
            mat1, mat2 = matCombo
            for comboSummary, combo in allCombos[sett][matCombo]:
                cubes = combo
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, comboSummary.mat1Spectra / comboSummary.mat2Spectra,
                                         label=f'{sett} {mat1.name}:{int(cubes[mat1].metadata.exposure)}ms {mat2.name}:{int(cubes[mat2].metadata.exposure)}ms')
    [ratioAxes[combo].legend() for combo in matCombos]

    comparisonDock = DockablePlotWindow("Correction Comparison")
    figs.append(comparisonDock)
    for sett in settings:
        settMatCombos = allCombos[sett].keys()  # Sometime we are looking at settings which don't have all the same matCombos. Only use the combos specific to this setting.
        means = totalMean[sett]
        fig6, scatterAx3 = comparisonDock.subplots(f"{sett} Uncorrected")
        scatterAx3.set_ylabel("Theoretical Ratio")
        scatterAx3.set_xlabel("Observed Ratio. No correction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in settMatCombos]
        scatterPointsX = [(meanValues[sett][matCombo].mat1Spectra / meanValues[sett][matCombo].mat2Spectra).mean() for
                          matCombo in settMatCombos]
        [scatterAx3.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in zip(scatterPointsX, scatterPointsY, settMatCombos)]
        x = np.array([1, max(scatterPointsX + scatterPointsY) * 1.05])
        scatterAx3.plot(x, x, label='1:1')
        scatterAx3.legend()

        fig4, scatterAx2 = comparisonDock.subplots(sett)  # A scatter plot of the theoretical vs observed reflectance ratio.
        scatterAx2.set_ylabel("Theoretical Ratio")
        scatterAx2.set_xlabel("Observed Ratio after Subtraction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in settMatCombos]
        scatterPointsX = [np.nanmean((meanValues[sett][matCombo].mat1Spectra - means.I0 * means.rExtra) / (
                meanValues[sett][matCombo].mat2Spectra - means.I0 * means.rExtra)) for matCombo in
                          settMatCombos]
        [scatterAx2.scatter(x, y, label=f'{matCombo[0].name}/{matCombo[1].name}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, settMatCombos)]
        x = np.array([1, max(scatterPointsX + scatterPointsY) * 1.05])
        scatterAx2.plot(x, x, label='1:1')
        scatterAx2.legend()
    return figs


def _generateOneRExtraCube(combo: CubeCombo, theoryR: t_.Dict[Material, pd.Series]) -> t_.Tuple[np.ndarray, np.ndarray]:
    """Given a combination of two PwsCubes imaging different materials and the theoretical reflectance for the materials
    imaged in the two PwsCubes this function will generate an estimation of the extra reflectance in the system.

    Args:
        combo: A combo of two PwsCubes imaging two different glass-material interfaces.
        theoryR: A dictionary providing Pandas `Series` giving the theoretically expected reflectance for each glass-material
            interface represented by the two PwsCubes.

    Returns:
        The first item is the array of the estimated extra reflectance of the system, expressed as values between 0 and
        1 (this is the same shape as the PwsCubes supplied to the function.) The second item is an estimate of how reliable
        each element in the array is.

    """
    data1 = combo.data1.data
    data2 = combo.data2.data
    T1 = np.array(theoryR[combo.mat1])[np.newaxis, np.newaxis, :]
    T2 = np.array(theoryR[combo.mat2])[np.newaxis, np.newaxis, :]
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
    weight = (data1-data2)**2 / (data1**2 + data2**2)  # The weight is the inverse of the variance. Higher weight = more reliable data.
    return arr, weight


def generateRExtraCubes(allCombos: t_.Dict[MCombo, t_.List[CubeCombo]], theoryR: t_.Dict[Material, pd.Series], numericalAperture: float) -> \
        t_.Tuple[pwsdt.ExtraReflectanceCube, t_.Dict[t_.Union[str, MCombo], np.ndarray]]:
    """Generate a series of extra reflectance cubes based on the input data.

    Args:
        allCombos: a dict of lists CubeCombos, each keyed by a 2-tuple of Materials.
        theoryR: the theoretically predicted reflectance for each material.
        numericalAperture: The numerical aperture that the PwsCubes were imaged at. The theoryR reflectances should have
            also been calculated at this NA

    Returns:
        An `ExtraReflectanceCube` object containing data from the weighted average of all measurements.
         A dictionary where the keys are material combos and the values are tuples of the weightedMean and the weight arrays.
    """
    rExtra: t_.Dict[MCombo, np.ndarray] = {}
    rExtraWeight: t_.Dict[MCombo, np.ndarray] = {}
    # Calculate weighted sum for all measurements within a certain material combo
    for matCombo, combosList in allCombos.items():
        logging.getLogger(__name__).info(f"Calculating rExtra for: {matCombo}")
        erCubes, weights = zip(*[_generateOneRExtraCube(combo, theoryR) for combo in combosList])
        weightSum = reduce(lambda x, y: x + y, weights)  # Sum of all weights
        weightedMean = reduce(lambda x, y: x + y, [cube*weight for cube, weight in zip(erCubes, weights)]) / weightSum  # Weighted mean of ER cubes
        meanWeight = weightSum / len(weights)
        rExtra[matCombo] = weightedMean
        rExtraWeight[matCombo] = meanWeight

    # Calculate weight mean accross all material combos
    erCubes = list(rExtra.values())
    weights = list(rExtraWeight.values())
    weightSum = reduce(lambda x, y: x + y, weights) # Sum of all weights
    weightedMean = reduce(lambda x, y: x + y, [cube * weight for cube, weight in zip(erCubes, weights)]) / weightSum  # Weighted mean of ER cubes
    # meanWeight = weightSum / len(weights)
    sampleCube: pwsdt.PwsCube = list(allCombos.values())[0][0].data1
    md = pwsdt.ERMetaData(sampleCube.metadata.dict, numericalAperture)
    erCube = pwsdt.ExtraReflectanceCube(weightedMean, sampleCube.wavelengths, md)
    return erCube, rExtra



