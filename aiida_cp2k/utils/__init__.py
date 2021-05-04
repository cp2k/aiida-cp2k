# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K utils"""

from .input_generator import Cp2kInput, add_restart_sections
from .parser import parse_cp2k_output
from .parser import parse_cp2k_output_advanced
from .parser import parse_cp2k_trajectory
from .workchains import merge_dict
from .workchains import merge_Dict
from .workchains import get_kinds_section
from .workchains import get_input_multiplicity
from .workchains import ot_has_small_bandgap
from .workchains import check_resize_unit_cell
from .workchains import resize_unit_cell
from .workchains import HARTREE2EV, HARTREE2KJMOL
from .workchains import seekpath_structure_analysis, update_input_dict_for_bands
