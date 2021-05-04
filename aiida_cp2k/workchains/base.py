# -*- coding: utf-8 -*-
"""Base work chain to run a CP2K calculation."""

from aiida.common import AttributeDict
from aiida.engine import BaseRestartWorkChain, ExitCode, ProcessHandlerReport, process_handler, while_
from aiida.orm import Dict
from aiida.plugins import CalculationFactory

from ..utils import add_restart_sections

Cp2kCalculation = CalculationFactory('cp2k')  # pylint: disable=invalid-name


class Cp2kBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a CP2K calculation with automated error handling and restarts."""

    _process_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(Cp2kBaseWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kCalculation, namespace='cp2k')

        spec.outline(
            cls.setup,
            while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        spec.expose_outputs(Cp2kCalculation)
        spec.output('final_input_parameters', valid_type=Dict, required=False,
                    help='The input parameters used for the final calculation.')

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """

        super(Cp2kBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(self.exposed_inputs(Cp2kCalculation, 'cp2k'))

    def results(self):
        super().results()
        if self.inputs.cp2k.parameters != self.ctx.inputs.parameters:
            self.out('final_input_parameters', self.ctx.inputs.parameters)



    @process_handler(priority=400, enabled=False)
    def resubmit_unconverged_geometry(self, calc):
        """Resubmit a calculation it is not converged, but can be recovered."""

        self.report("Entering the process handler.")

        content_string = calc.outputs.retrieved.get_object_content(calc.get_attribute('output_filename'))

        time_not_exceeded = "PROGRAM ENDED AT"
        time_exceeded = "exceeded requested execution time"
        one_step_done = "Max. gradient              ="
        self.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
        params = self.ctx.inputs.parameters

        # If the problem is recoverable then do restart
        if (time_not_exceeded not in content_string or time_exceeded in content_string) and one_step_done in content_string:  # pylint: disable=line-too-long
            try:
                # Firts check if all the restart keys are present in the input dictionary
                wf_rest_fname_pointer = params['FORCE_EVAL']['DFT']['RESTART_FILE_NAME']
                scf_guess_pointer = params['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS']
                restart_fname_pointer = params['EXT_RESTART']['RESTART_FILE_NAME']

                # Also check if they all have the right value
                if not (wf_rest_fname_pointer == './parent_calc/aiida-RESTART.wfn' and
                        scf_guess_pointer == 'RESTART' and
                        restart_fname_pointer == './parent_calc/aiida-1.restart'):

                    # If some values are incorrect add them to the input dictionary
                    params = add_restart_sections(params)

            # If not all the restart keys are present, adding them to the input dictionary
            except (AttributeError, KeyError):
                params = add_restart_sections(params)

            # Might be able to solve the problem
            self.ctx.inputs.parameters = params  # params (new or old ones) that for sure
            # include the necessary restart key-value pairs
            self.report(
                "The CP2K calculation wasn't completed. The restart of the calculation might be able to "
                "fix the problem.")
            return ProcessHandlerReport(do_break=True)

        # If the problem is not recoverable
        if (time_not_exceeded not in content_string or
                time_exceeded in content_string) and one_step_done not in content_string:

            self.report("It seems that the restart of CP2K calculation wouldn't be able to fix the problem. "
                             "Sending a signal to stop the Base work chain.")

            # Signaling to the base work chain that the problem could not be recovered.
            return ProcessHandlerReport(True, ExitCode(1))

        # If everything is alright
        return None

    @process_handler(priority=350, enabled=False)
    def resubmit_cellopt_for_final_check(self, calc):
        """Resubmit a cell optimization if it required more than 3 steps to converge."""

        self.report("Entering the process handler.")

        content_string = calc.outputs.retrieved.get_object_content(calc.get_attribute('output_filename'))

        steps_done = content_string.count('Informations at step')

        self.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
        params = self.ctx.inputs.parameters

        too_many_steps = steps_done > 5
        if too_many_steps:
            try:
                # Firts check if all the restart keys are present in the input dictionary
                wf_rest_fname_pointer = params['FORCE_EVAL']['DFT']['RESTART_FILE_NAME']
                scf_guess_pointer = params['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS']
                restart_fname_pointer = params['EXT_RESTART']['RESTART_FILE_NAME']

                # Also check if they all have the right value
                if not (wf_rest_fname_pointer == './parent_calc/aiida-RESTART.wfn' and
                    scf_guess_pointer == 'RESTART' and
                    restart_fname_pointer == './parent_calc/aiida-1.restart'):

                    # If some values are incorrect add them to the input dictionary
                    params = add_restart_sections(params)

            # If not all the restart keys are present, adding them to the input dictionary
            except KeyError:
                params = add_restart_sections(params)

            # Might be able to solve the problem
            self.ctx.inputs.parameters = params  # params (new or old ones) that for sure
            # include the necessary restart key-value pairs
            self.report(
                "The CP2K cell opt converged but required more than 3 steps."
                "I will restart it for final convergence")
            return ProcessHandlerReport(do_break=True)

        return None
