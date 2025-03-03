#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Any, Dict
import glob
import yaml


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


TOP_LEVEL_ITEMS = {
    "compilation_database_dir",
    "output_directory",
    "debug_mode",
    "add_compile_flags",
    "remove_compile_flags",
    "query_driver",
    "user_data",
    "diagrams",
}


DIAGRAMS_LEVEL_ITEMS = {
    "type",
    "glob",
    "relative_to",
    "include_relations_also_as_members",
    "generate_method_arguments",
    "generate_concept_requirements",
    "using_namespace",
    "generate_packages",
    "package_type",
    "include",
    "exclude",
    "layout",
    "plantuml",
    "mermaid",
    "graphml",
}


class Config:

    def __init__(self, params):
        if not isinstance(params, dict):
            raise RuntimeError("invalid argument - dict expected")
        self.params: Dict[Any, Any] = params

    def get(self, item):
        return self.params.get(item)


def get_base_directory(value_path, relative_to_value):
    if relative_to_value:
        return relative_to_value
    if os.path.isdir(value_path):
        return value_path
    return os.path.dirname(value_path)


def find_input_files(glob_list, base_dir_path):
    if not glob_list:
        return []
    ret_list = []
    for item in glob_list:
        if not isinstance(item, str):
            _LOGGER.warning("glob unsupported value type: %s %s", item, type(item))
            continue
        found = glob.glob(item, root_dir=base_dir_path, recursive=True)
        found_list = [os.path.join(base_dir_path, item) for item in found]
        ret_list.extend(found_list)
    ret_set = set(ret_list)  ## remove repetitions
    ret_list = list(ret_set)
    return ret_list


def read_config(config_path) -> Config:
    with open(config_path, "r", encoding="utf-8") as yamlfile:
        params_dict: Dict[Any, Any] = yaml.safe_load(yamlfile)
        return Config(params_dict)
