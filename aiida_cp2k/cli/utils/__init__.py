"""Some helpers for writing CLI functions"""

# pylint: disable=import-outside-toplevel

import os

import click

# the following 2 methods originated from aiiida-quantumespresso


def echo_process_results(node):
    """Display a formatted table of the outputs registered for the given process node.
    :param node: the `ProcessNode` of a terminated process
    """

    from aiida.cmdline.utils.common import get_node_info

    class_name = node.process_class.__name__

    if hasattr(node, 'dry_run_info'):
        # It is a dry-run: get the information and print it
        rel_path = os.path.relpath(node.dry_run_info['folder'])
        click.echo("-> Files created in folder '{}'".format(rel_path))
        click.echo("-> Submission script filename: '{}'".format(node.dry_run_info['script_filename']))
        return

    if node.is_finished and node.exit_message:
        state = '{} [{}] `{}`'.format(node.process_state.value, node.exit_status, node.exit_message)
    elif node.is_finished:
        state = '{} [{}]'.format(node.process_state.value, node.exit_status)
    else:
        state = node.process_state.value

    click.echo("{}<{}> terminated with state: {}]\n".format(class_name, node.pk, state))
    click.echo(get_node_info(node))


def launch_process(process, daemon, **inputs):
    """Launch a process with the given inputs.
    If not sent to the daemon, the results will be displayed after the calculation finishes.
    :param process: the process class
    :param daemon: boolean, if True will submit to the daemon instead of running in current interpreter
    :param inputs: inputs for the process
    """
    from aiida.engine import launch, Process, ProcessBuilder

    if isinstance(process, ProcessBuilder):
        process_name = process.process_class.__name__
    elif issubclass(process, Process):
        process_name = process.__name__
    else:
        raise TypeError('invalid type for process: {}'.format(process))

    if daemon:
        node = launch.submit(process, **inputs)
        click.echo('Submitted {}<{}> to the daemon'.format(process_name, node.pk))
    else:
        if inputs.get('metadata', {}).get('dry_run', False):
            click.echo('Running a dry run for {}...'.format(process_name))
        else:
            click.echo('Running a {}...'.format(process_name))
        _, node = launch.run_get_node(process, **inputs)
        echo_process_results(node)
