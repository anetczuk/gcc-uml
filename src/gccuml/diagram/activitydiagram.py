# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging

from typing import Dict

from gccuml.diagram import activitydata
from gccuml.diagram.plantuml.activitydiagram import ActivityDiagramGenerator as PlantUmlGenerator
from gccuml.diagram.graphviz.activitygraph import ActivityGraphGenerator as DotGenerator


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


def generate_diagram(engine: str, data_dict: Dict[str, activitydata.ActivityData], out_path):
    if engine == "dot":
        generate_dot(data_dict, out_path)
        return
    if engine == "plantuml":
        generate_plantuml(data_dict, out_path)
        return
    raise RuntimeError(f"unknown engine: {engine}")


def generate_dot(data_dict: Dict[str, activitydata.ActivityData], out_path):
    generator = DotGenerator(data_dict)
    generator.generate(out_path)


def generate_plantuml(data_dict: Dict[str, activitydata.ActivityData], out_path):
    generator = PlantUmlGenerator(data_dict)
    generator.generate(out_path)
