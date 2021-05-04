# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K utilities for workchains"""

from aiida.engine import calcfunction
from aiida.orm import Dict
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name

HARTREE2EV = 27.211399
HARTREE2KJMOL = 2625.500

VAL_ELEC = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 3,
    "C": 4,
    "N": 5,
    "O": 6,
    "F": 7,
    "Ne": 8,
    "Na": 9,
    "Mg": 2,
    "Al": 3,
    "Si": 4,
    "P": 5,
    "S": 6,
    "Cl": 7,
    "Ar": 8,
    "K": 9,
    "Ca": 10,
    "Sc": 11,
    "Ti": 12,
    "V": 13,
    "Cr": 14,
    "Mn": 15,
    "Fe": 16,
    "Co": 17,
    "Ni": 18,
    "Cu": 19,
    "Zn": 12,
    "Zr": 12,
}


def merge_dict(dct, merge_dct):
    """Recursive dict merge.

    Taken from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9

    Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, merge_dict recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct (overwrites dct data if in both)
    :return: None
    """
    import collections
    for k, _ in merge_dct.items():  # it was .iteritems() in python2
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], collections.Mapping)):
            merge_dict(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


@calcfunction
def merge_Dict(dict1, dict2):  # pylint: disable=invalid-name
    """Make all the data in the second Dict overwrite the corrisponding data in the first Dict."""
    result = dict1.get_dict()
    merge_dict(result, dict2.get_dict())
    return Dict(dict=result)


def get_kinds_section(structure, protocol_settings):
    """Write the &KIND sections given the structure and the settings_dict"""
    kinds = []
    all_atoms = set(structure.get_ase().get_chemical_symbols())
    for atom in all_atoms:
        kinds.append({
            '_': atom,
            'BASIS_SET': protocol_settings['basis_set'][atom],
            'POTENTIAL': protocol_settings['pseudopotential'][atom],
            'MAGNETIZATION': protocol_settings['initial_magnetization'][atom],
        })
    return {'FORCE_EVAL': {'SUBSYS': {'KIND': kinds}}}


def get_input_multiplicity(structure, protocol_settings):
    """ Compute the total multiplicity of the structure,
    by summing the atomic magnetizations:
    multiplicity = 1 + sum_i ( natoms_i * magnetization_i ), for each atom_type i
    """
    multiplicity = 1
    all_atoms = structure.get_ase().get_chemical_symbols()
    for key, value in protocol_settings['initial_magnetization'].items():
        multiplicity += all_atoms.count(key) * value
    multiplicity = int(round(multiplicity))
    multiplicity_dict = {'FORCE_EVAL': {'DFT': {'MULTIPLICITY': multiplicity}}}
    if multiplicity != 1:
        multiplicity_dict['FORCE_EVAL']['DFT']['UKS'] = True
    return multiplicity_dict


def ot_has_small_bandgap(cp2k_input, cp2k_output, bandgap_thr_ev):
    """ Returns True if the calculation used OT and had a smaller bandgap then the guess needed for the OT.
    (NOTE: It has been observed also negative bandgap with OT in CP2K!)
    cp2k_input: dict
    cp2k_output: dict
    bandgap_thr_ev: float [eV]
    """
    list_true = [True, 'T', 't', '.TRUE.', 'True', 'true']  #add more?
    try:
        ot_settings = cp2k_input['FORCE_EVAL']['DFT']['SCF']['OT']
        if '_' not in ot_settings.keys() or ot_settings['_'] in list_true:  #pylint: disable=simplifiable-if-statement
            using_ot = True
        else:
            using_ot = False
    except KeyError:
        using_ot = False
    min_bandgap_ev = min(cp2k_output["bandgap_spin1_au"], cp2k_output["bandgap_spin2_au"]) * HARTREE2EV
    is_bandgap_small = (min_bandgap_ev < bandgap_thr_ev)
    return using_ot and is_bandgap_small


@calcfunction
def check_resize_unit_cell(struct, threshold):  #pylint: disable=too-many-locals
    """Returns the multiplication factors for the cell vectors to respect, in every direction:
    min(perpendicular_width) > threshold.
    """
    from math import cos, sin, sqrt, fabs, ceil
    import numpy as np

    # Parsing structure's cell
    def angle(vect1, vect2):
        return np.arccos(np.dot(vect1, vect2) / (np.linalg.norm(vect1) * np.linalg.norm(vect2)))

    a_len = np.linalg.norm(struct.cell[0])
    b_len = np.linalg.norm(struct.cell[1])
    c_len = np.linalg.norm(struct.cell[2])

    alpha = angle(struct.cell[1], struct.cell[2])
    beta = angle(struct.cell[0], struct.cell[2])
    gamma = angle(struct.cell[0], struct.cell[1])

    # Computing triangular cell matrix
    vol = np.sqrt(1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + 2 * cos(alpha) * cos(beta) * cos(gamma))
    cell = np.zeros((3, 3))
    cell[0, :] = [a_len, 0, 0]
    cell[1, :] = [b_len * cos(gamma), b_len * sin(gamma), 0]
    cell[2, :] = [
        c_len * cos(beta), c_len * (cos(alpha) - cos(beta) * cos(gamma)) / (sin(gamma)), c_len * vol / sin(gamma)
    ]
    cell = np.array(cell)

    # Computing perpendicular widths, as implemented in Raspa
    # for the check (simplified for triangular cell matrix)
    axc1 = cell[0, 0] * cell[2, 2]
    axc2 = -cell[0, 0] * cell[2, 1]
    bxc1 = cell[1, 1] * cell[2, 2]
    bxc2 = -cell[1, 0] * cell[2, 2]
    bxc3 = cell[1, 0] * cell[2, 1] - cell[1, 1] * cell[2, 0]
    det = fabs(cell[0, 0] * cell[1, 1] * cell[2, 2])
    perpwidth = np.zeros(3)
    perpwidth[0] = det / sqrt(bxc1**2 + bxc2**2 + bxc3**2)
    perpwidth[1] = det / sqrt(axc1**2 + axc2**2)
    perpwidth[2] = cell[2, 2]

    #prevent from crashing if threshold.value is zero
    if threshold.value == 0:
        thr = 0.1
    else:
        thr = threshold.value

    resize = {
        'nx': int(ceil(thr / perpwidth[0])),
        'ny': int(ceil(thr / perpwidth[1])),
        'nz': int(ceil(thr / perpwidth[2]))
    }
    return Dict(dict=resize)


@calcfunction
def resize_unit_cell(struct, resize):
    """Resize the StructureData according to the resize Dict"""
    resize_tuple = tuple([resize[x] for x in ['nx', 'ny', 'nz']])
    return StructureData(ase=struct.get_ase().repeat(resize_tuple))


def add_condband(structure):
    """Add 20% of conduction bands to the CP2K input. If 20 % is 0, then add only one."""
    total = 0
    for symbol in structure.get_ase().get_chemical_symbols():
        total += VAL_ELEC[symbol]
    added_mos = total // 10  # 20% of conduction band
    if added_mos == 0:
        added_mos = 1
    return added_mos


def update_input_dict_for_bands(input_dict, seekpath, structure):
    """Insert kpoint path into the input dictonary of CP2K."""

    i_dict = input_dict.get_dict()

    path = seekpath.dict['path']
    coords = seekpath.dict['point_coords']

    kpath = []
    for pnt in path:
        pnt1 = pnt[0] + ' ' + " ".join(str(x) for x in coords[pnt[0]])
        pnt2 = pnt[1] + ' ' + " ".join(str(x) for x in coords[pnt[1]])
        kpath.append({'_': "", 'UNITS': 'B_VECTOR', 'NPOINTS': 10, 'SPECIAL_POINT': [pnt1, pnt2]})

    kpath_dict = {'FORCE_EVAL': {'DFT': {'PRINT': {'BAND_STRUCTURE': {'KPOINT_SET': kpath}}}}}
    merge_dict(i_dict, kpath_dict)

    added_mos = {'FORCE_EVAL': {'DFT': {'SCF': {'ADDED_MOS': add_condband(structure)}}}}
    merge_dict(i_dict, added_mos)

    return Dict(dict=i_dict)


@calcfunction
def seekpath_structure_analysis(structure, parameters):
    """This calcfunction will take a structure and pass it through SeeKpath to get the
    primitive cell and the path of high symmetry k-points through its Brillouin zone.

    Note that the returned primitive cell may differ from the original structure in
    which case the k-points are only congruent with the primitive cell.
    """

    from aiida.tools import get_kpoints_path
    return get_kpoints_path(structure, **parameters.get_dict())
