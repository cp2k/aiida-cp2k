# -*- coding: utf-8 -*-
"""Command line utilities to create and inspect `StructureData` nodes from CP2K input files."""

import click

from aiida.cmdline.params import options
from aiida.cmdline.utils import decorators, echo

from . import cmd_data
from ..utils.structure import structure_from_cp2k_inp


@cmd_data.group('structure')
def cmd_structure():
    """Commands to create and inspect `StructureData` nodes from CP2K input."""


@cmd_structure.command('import')
@click.argument('filename', type=click.File('r'))
@options.DRY_RUN()
@decorators.with_dbenv()
def cmd_import(filename, dry_run):
    """Import a `StructureData` from a CP2K input file."""

    try:
        structure = structure_from_cp2k_inp(filename)
    except ValueError as exc:
        echo.echo_critical(str(exc))

    formula = structure.get_formula()

    if dry_run:
        echo.echo_success('parsed structure with formula {}'.format(formula))
    else:
        structure.store()
        echo.echo_success('parsed and stored StructureData<{}> with formula {}'.format(structure.pk, formula))
