# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel
"""Base workchain command"""

import click

from aiida.cmdline.params import options, types
from aiida.cmdline.utils import decorators, echo

from . import cmd_launch
from ..utils import cp2k_options, launch_process
from ..utils.structure import structure_from_cp2k_inp


@cmd_launch.command('base')
@options.CODE(required=True, type=types.CodeParamType(entry_point='cp2k'))
@click.argument('cp2k-input-file', type=click.File('r'))
@click.option('-l', '--label', type=str)
@click.option('-m', '--description', type=str)
@cp2k_options.STRUCTURE()
@cp2k_options.DAEMON()
@cp2k_options.MAX_NUM_MACHINES()
@cp2k_options.MAX_WALLCLOCK_SECONDS()
@decorators.with_dbenv()
def cmd_launch_workflow(code, daemon, cp2k_input_file, label, description, structure, max_num_machines,
                        max_wallclock_seconds):
    """Run a CP2K calculation with a given input file through AiiDA"""
    # pylint: disable=too-many-arguments,too-many-branches,too-many-statements

    from aiida.orm import Dict
    from aiida.plugins import WorkflowFactory
    from aiida.orm.nodes.data.structure import StructureData
    from cp2k_input_tools.parser import CP2KInputParserSimplified

    parser = CP2KInputParserSimplified(key_trafo=str.upper,
                                       multi_value_unpack=False,
                                       repeated_section_unpack=False,
                                       level_reduction_blacklist=["KIND"])
    tree = parser.parse(cp2k_input_file)

    try:
        tree["FORCE_EVAL"]["SUBSYS"].pop("COORD")
        structure_in_config = True
    except KeyError:
        structure_in_config = False

    try:
        coord_file_from_config = tree["FORCE_EVAL"]["SUBSYS"]["TOPOLOGY"].pop("COORD_FILE_NAME")
    except KeyError:
        coord_file_from_config = None

    builder = WorkflowFactory('cp2k.base').get_builder()
    builder.cp2k.code = code

    if structure:
        builder.cp2k.structure = structure

        if coord_file_from_config:
            echo.echo_info(
                "The explicitly given structure will override the structure file referenced in the input file")

        if structure_in_config:
            echo.echo_info("The explicitly given structure will override the structure in the input file")

    elif structure_in_config:
        try:
            cp2k_input_file.seek(0)
            builder.cp2k.structure = structure_from_cp2k_inp(cp2k_input_file)
            builder.cp2k.structure.store()
            echo.echo("Created StructureData<{}> from file {}]\n".format(builder.cp2k.structure.pk,
                                                                         cp2k_input_file.name))
        except ValueError as err:
            echo.echo_critical(str(err))

    elif coord_file_from_config:
        try:
            import ase.io
        except ImportError:
            echo.echo_critical('You have not installed the package ase. \nYou can install it with: pip install ase')

        try:
            asecell = ase.io.read(coord_file_from_config)
            builder.cp2k.structure = StructureData(ase=asecell)
            builder.cp2k.structure.store()
            echo.echo("Created StructureData<{}> from file {}]\n".format(builder.cp2k.structure.pk,
                                                                         coord_file_from_config))
        except ValueError as err:
            echo.echo_critical(str(err))
    else:
        echo.echo_critical("No structure found/referenced in the input file and not set explicitly")

    builder.cp2k.metadata.options = {
        "resources": {
            "num_machines": max_num_machines,
        },
        'max_wallclock_seconds': int(max_wallclock_seconds),
    }
    builder.cp2k.parameters = Dict(dict=tree)

    if label:
        builder.metadata.label = label

    if description:
        builder.metadata.description = description

    launch_process(builder, daemon)
