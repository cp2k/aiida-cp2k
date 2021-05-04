# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run simple Band Structure calculation"""

from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import click
import numpy as np
from ase.atoms import Atoms

from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData, StructureData)
from aiida.common import NotExistent
from aiida.plugins import WorkflowFactory

Cp2kBandsWorkChain = WorkflowFactory('cp2k.bands')


def example_bands(cp2k_code):
    """Run simple Band Structure calculation"""

    print("Computing Band Structure of Si...")

    pwd = os.path.dirname(os.path.realpath(__file__))

    # structure
    positions = [
        [0.0000000000, 0.0000000000, 2.6954627656],
        [4.0431941484, 4.0431941484, 4.0431941484],
    ]
    cell = [
        [0.0, 2.69546276561, 2.69546276561],
        [2.69546276561, 0.0, 2.69546276561],
        [2.69546276561, 2.69546276561, 0.0],
    ]
    atoms = Atoms('Si2', positions=positions, cell=cell, pbc=[True, True, True])
    structure = StructureData(ase=atoms)

    # basis set
    basis_file = SinglefileData(file=os.path.join(pwd, "..", "files", "BASIS_MOLOPT"))

    # pseudopotentials
    pseudo_file = SinglefileData(file=os.path.join(pwd, "..", "files", "GTH_POTENTIALS"))

    # parameters
    parameters = Dict(
        dict={
            'FORCE_EVAL': {
                'METHOD': 'Quickstep',
                'DFT': {
                    'CHARGE': 0,
                    'KPOINTS': {
                        'SCHEME MONKHORST-PACK': '1 1 1',
                        'SYMMETRY': 'OFF',
                        'WAVEFUNCTIONS': 'REAL',
                        'FULL_GRID': '.TRUE.',
                        'PARALLEL_GROUP_SIZE': 0,
                    },
                    'MGRID': {
                        'CUTOFF': 600,
                        'NGRIDS': 4,
                        'REL_CUTOFF': 50,
                    },
                    'UKS': False,
                    'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
                    'POTENTIAL_FILE_NAME': 'GTH_POTENTIALS',
                    'QS': {
                        'METHOD': 'GPW',
                        'EXTRAPOLATION': 'USE_GUESS'
                    },
                    'POISSON': {
                        'PERIODIC': 'XYZ',
                    },
                    'SCF': {
                        'EPS_SCF': 1.0E-4,
                        'SMEAR': {
                            'METHOD': 'FERMI_DIRAC',
                            'ELECTRONIC_TEMPERATURE': 300
                        },
                        'DIAGONALIZATION': {
                            'ALGORITHM': 'STANDARD',
                            'EPS_ADAPT': 0.01
                        },
                        'MIXING': {
                            'METHOD': 'BROYDEN_MIXING',
                            'ALPHA': 0.2,
                            'BETA': 1.5,
                            'NBROYDEN': 8
                        },
                    },
                    'XC': {
                        'XC_FUNCTIONAL': {
                            '_': 'PBE',
                        },
                    },
                },
                'SUBSYS': {
                    'KIND': [{
                        '_': 'Si',
                        'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                        'POTENTIAL': 'GTH-LDA-q4'
                    },]
                },
                'PRINT': {  # this is to print forces (may be necessary for problems
                    # detection)
                    'FORCES': {
                        '_': 'ON',
                    }
                },
            },
            'GLOBAL': {
                "EXTENDED_FFT_LENGTHS": True,  # Needed for large systems
            }
        })

    # Construct process builder
    builder = Cp2kBandsWorkChain.get_builder()
    builder.structure = structure
    builder.parameters = parameters
    builder.cp2k_base.cp2k.code = cp2k_code
    builder.cp2k_base.cp2k.file = {
        'basis': basis_file,
        'pseudo': pseudo_file,
    }

    builder.cp2k_base.cp2k.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }

    builder.cp2k_base.cp2k.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("submitted calculation...")
    calc = run(builder)

    bands = calc['output_bands']

    # check bands
    expected_gamma_kpoint = np.array([-5.71237757, 6.5718575, 6.5718575, 6.5718575, 8.88653953])

    if bands.get_kpoints().shape == (66, 3):
        print("OK, got expected kpoints set size.")
    else:
        print("Got unexpected kpoints set.")
        sys.exit(3)

    if bands.get_bands().shape == (66, 5):
        print("OK, got expected bands set size.")
    else:
        print("Got unexpected bands set.")
        sys.exit(3)

    if abs(max(bands.get_bands()[0] - expected_gamma_kpoint)) < 1e-7:
        print("Ok, got expected energy levels at GAMMA point.")
    else:
        print("Got unexpected energy levels at GAMMA point.")
        sys.exit(3)

    sys.exit(0)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example_bands(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
