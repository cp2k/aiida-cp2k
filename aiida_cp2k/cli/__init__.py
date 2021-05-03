# -*- coding: utf-8 -*-

# pylint: disable=wrong-import-position,wildcard-import
"""Base command line interface module to wire up subcommands and loading the profile."""

import click
import click_completion

from aiida.cmdline.params import options, types

# Activate the completion of parameter types provided by the click_completion package
click_completion.init()


@click.group('aiida-cp2k', context_settings={'help_option_names': ['-h', '--help']})
@options.PROFILE(type=types.ProfileParamType(load_profile=True))
def cmd_root(profile):  # pylint: disable=unused-argument
    """CLI for the `aiida-cp2k` plugin."""


from .data import cmd_structure
from .workflows import cmd_workflow
