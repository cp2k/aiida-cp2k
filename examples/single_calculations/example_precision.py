# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test structure roundtrip precision ase->aiida->cp2k->aiida->ase"""
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import ase.build
import click
import numpy as np

from aiida.orm import (Code, Dict, SinglefileData, StructureData)
from aiida.engine import run
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

Cp2kCalculation = CalculationFactory('cp2k')


def example_precision(cp2k_code):
    """Test structure roundtrip precision ase->aiida->cp2k->aiida->ase"""

    print("Testing structure roundtrip precision ase->aiida->cp2k->aiida->ase...")

    pwd = os.path.dirname(os.path.realpath(__file__))

    # structure
    epsilon = 1e-10  # expected precision in Angstrom
    dist = 0.74 + epsilon
    positions = [(0, 0, 0), (0, 0, dist)]
    cell = np.diag([4, -4, 4 + epsilon])
    atoms = ase.Atoms('H2', positions=positions, cell=cell)
    structure = StructureData(ase=atoms)

    # basis set
    basis_file = SinglefileData(file=os.path.join(pwd, "..", "files", "BASIS_MOLOPT"))

    # pseudopotentials
    pseudo_file = SinglefileData(file=os.path.join(pwd, "..", "files", "GTH_POTENTIALS"))

    # parameters
    parameters = Dict(
        dict={
            'GLOBAL': {
                'RUN_TYPE': 'MD',
            },
            'MOTION': {
                'MD': {
                    'TIMESTEP': 0.0,  # do not move atoms
                    'STEPS': 1,
                },
            },
            'FORCE_EVAL': {
                'METHOD': 'Quickstep',
                'DFT': {
                    'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
                    'POTENTIAL_FILE_NAME': 'GTH_POTENTIALS',
                    'SCF': {
                        'MAX_SCF': 1,
                    },
                    'XC': {
                        'XC_FUNCTIONAL': {
                            '_': 'LDA',
                        },
                    },
                },
                'SUBSYS': {
                    'KIND': {
                        '_': 'DEFAULT',
                        'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                        'POTENTIAL': 'GTH-LDA',
                    },
                },
            },
        })

    # resources
    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 60 * 60,
    }

    inputs = {
        'structure': structure,
        'parameters': parameters,
        'code': cp2k_code,
        'file': {
            'basis': basis_file,
            'pseudo': pseudo_file,
        },
        'metadata': {
            'options': options,
        }
    }

    print("submitted calculation...")
    calc = run(Cp2kCalculation, **inputs)

    # check structure preservation
    atoms2 = calc['output_structure'].get_ase()

    # zeros should be preserved exactly
    if np.all(atoms2.positions[0] == 0.0):
        print("OK, zeros in structure were preserved exactly")
    else:
        print("ERROR!")
        print("Zeros in structure changed: ", atoms2.positions[0])
        sys.exit(3)

    # other values should be preserved with epsilon precision
    dist2 = atoms2.get_distance(0, 1)
    if abs(dist2 - dist) < epsilon:
        print("OK, structure preserved with %.1e Angstrom precision" % epsilon)
    else:
        print("ERROR!")
        print("Structure changed by %e Angstrom" % abs(dist - dist2))
        sys.exit(3)

    # check cell preservation
    cell_diff = np.amax(np.abs(atoms2.cell - cell))
    if cell_diff < epsilon:
        print("OK, cell preserved with %.1e Angstrom precision" % epsilon)
    else:
        print("ERROR!")
        print("Cell changed by %e Angstrom" % cell_diff)
        sys.exit(3)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example_precision(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter