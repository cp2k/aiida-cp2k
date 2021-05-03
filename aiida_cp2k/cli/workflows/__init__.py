# -*- coding: utf-8 -*-
# pylint: disable=cyclic-import,unused-import,wrong-import-position
"""Base workflow commands and sub-commands"""

from .. import cmd_root


@cmd_root.group("workflow")
def cmd_workflow():
    """Commands to launch and interact with workflows."""


@cmd_workflow.group("launch")
def cmd_launch():
    """Launch workflow."""


from .base import cmd_launch_workflow
