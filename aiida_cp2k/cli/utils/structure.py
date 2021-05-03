# -*- coding: utf-8 -*-
"""Helper functions for building CLI functions dealing with structures"""

import re

import numpy as np


def structure_from_cp2k_inp(filename):
    """Create an AiiDA StructureData from a structure inside a CP2K input file"""
    # pylint: disable=import-outside-toplevel,invalid-name,too-many-locals,too-many-statements,too-many-branches

    from cp2k_input_tools.parser import CP2KInputParser
    from aiida.orm.nodes.data.structure import StructureData, Kind, Site, symop_fract_from_ortho
    from ase.geometry.cell import cell_to_cellpar, cellpar_to_cell
    import ase.io

    # the following was taken from aiida-quantumespresso
    VALID_ELEMENTS_REGEX = re.compile(
        r"""
    ^(
      H  | He |
      Li | Be | B  | C  | N  | O  | F  | Ne |
      Na | Mg | Al | Si | P  | S  | Cl | Ar |
      K  | Ca | Sc | Ti | V  | Cr | Mn | Fe | Co | Ni | Cu | Zn | Ga | Ge | As | Se | Br | Kr |
      Rb | Sr | Y  | Zr | Nb | Mo | Tc | Ru | Rh | Pd | Ag | Cd | In | Sn | Sb | Te | I  | Xe |
      Cs | Ba | Hf | Ta | W  | Re | Os | Ir | Pt | Au | Hg | Tl | Pb | Bi | Po | At | Rn |
      Fr | Ra | Rf | Db | Sg | Bh | Hs | Mt |
      La | Ce | Pr | Nd | Pm | Sm | Eu | Gd | Tb | Dy | Ho | Er | Tm | Yb | Lu | # Lanthanides
      Ac | Th | Pa | U  | Np | Pu | Am | Cm | Bk | Cf | Es | Fm | Md | No | Lr | # Actinides
      )
    """, re.VERBOSE | re.IGNORECASE)

    parser = CP2KInputParser()
    tree = parser.parse(filename)
    force_eval_no = -1
    force_eval = None

    for force_eval_no, force_eval in enumerate(tree['+force_eval']):
        try:
            cell = force_eval['+subsys']['+cell']
            kinds = force_eval['+subsys']['+kind']
            break  # for now grab the first &COORD found
        except KeyError:
            continue
    else:
        raise ValueError('no CELL, or KIND found in the given input file')

    # CP2K can get its cell information in two ways:
    # - A, B, C: cell vectors
    # - ABC: scaling of cell vectors, ALPHA_BETA_GAMMA: angles between the cell vectors (optional)

    if 'a' in cell:
        unit_cell = np.array([cell['a'], cell['b'], cell['c']])  # unit vectors given
        cellpar = cell_to_cellpar(unit_cell)
    elif 'abc' in cell:
        cellpar = cell['abc'] + cell.get('alpha_beta_gamma', [90., 90., 90.])
        unit_cell = cellpar_to_cell(cellpar)
    else:
        raise ValueError('incomplete &CELL section')

    pbc = [c in cell.get('periodic', 'XYZ') for c in 'XYZ']

    structure = StructureData(cell=unit_cell, pbc=pbc)

    if force_eval['+subsys'].get('+coord', {}).get('scaled', False):
        tmat = symop_fract_from_ortho(cellpar)
    else:
        tmat = np.eye(3)

    for kind in kinds:
        name = kind['_']

        try:
            # prefer the ELEMENT keyword, fallback to extracting from name
            element = kind.get('element', VALID_ELEMENTS_REGEX.search(name)[0])
        except TypeError:
            raise ValueError('ELEMENT not set and unable to extract from {name}'.format(name=name))

        structure.append_kind(Kind(name=name, symbols=element))

    try:
        structfn = force_eval["+subsys"]["+topology"]["coord_file_name"]
        atoms = ase.io.read(structfn)

        for name, position in zip(atoms.symbols, atoms.positions):
            structure.append_site(Site(kind_name=name, position=tmat @ np.array(position)))

    except KeyError:
        for name, position, _ in parser.coords(force_eval_no):
            # positions can be scaled, apply transformation matrix
            structure.append_site(Site(kind_name=name, position=tmat @ np.array(position)))

    return structure
