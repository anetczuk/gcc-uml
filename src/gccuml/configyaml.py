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


# include - definition of inclusion patterns:
#     namespaces - list of namespaces to include
#     relationships - list of relationships to include
#     elements - list of elements, i.e. specific classes, enums, templates to include
#     element_types - list of element types e.g. enum, class, concept:
#        - class
#        - enum
#        - concept
#        - method
#        - function
#        - function_template
#        - lambda
#     access - list of visibility scopes to include (e.g. private)
#     subclasses - include only subclasses of specified classes (and themselves)
#     specializations - include all specializations or instantiations of a given template
#     dependants - include all classes, which depend on the specified class
#     dependencies - include all classes, which are dependencies of the specified class
#     context - include only entities in direct relationship with specified classes
#
# exclude - definition of exclusion patterns:
#     namespaces - list of namespaces to exclude
#     relationships - list of relationships to exclude
#     elements - list of elements, i.e. specific classes, enums, templates to exclude
#     element_types - list of element types e.g. enum, class, concept
#        - class
#        - enum
#        - concept
#        - method
#        - function
#        - function_template
#        - lambda
#     access - list of visibility scopes to exclude (e.g. private)
#     subclasses - exclude subclasses of specified classes (and themselves)
#     specializations - exclude all specializations or instantiations of a given template
#     dependants - exclude all classes, which depend on the specified class
#     dependencies - exclude all classes, which are dependencies of the specified class
#     context - exclude only entities in direct relationship with specified classes


# filter_t:
#     namespaces: !optional [regex_or_string_t]
#     modules: !optional [regex_or_string_t]
#     elements: !optional [element_filter_t]
#     element_types: !optional [element_types_filter_t]
#     relationships: !optional [relationship_filter_t]
#     access: !optional [access_filter_t]
#     module_access: !optional [module_access_filter_t]
#     subclasses: !optional [regex_or_string_t]
#     parents: !optional [regex_or_string_t]
#     specializations: !optional [regex_or_string_t]
#     dependants: !optional [regex_or_string_t]
#     dependencies: !optional [regex_or_string_t]
#     context: !optional [context_filter_t]
#     paths: !optional [string]
#     method_types: !optional [method_type_filter_t]
#     callee_types: !optional [callee_type_filter_t]
#     anyof: !optional filter_t
#     allof: !optional filter_t
class Filter:
    def __init__(self, include_dict=None, exclude_dict=None):
        if include_dict is None:
            include_dict = {}
        if exclude_dict is None:
            exclude_dict = {}
        self.include_dict = include_dict
        self.exclude_dict = exclude_dict  ## 'exclude' is stronger than 'include'

    @staticmethod
    def create(diagram_dict):
        include_data = diagram_dict.get("include")
        exclude_data = diagram_dict.get("exclude")
        return Filter(include_data, exclude_data)

    def check_include_namespace(self, namespace_list) -> bool:
        ns_string = "::".join(namespace_list)

        exclude_namespaces = self.exclude_dict.get("namespaces")
        if exclude_namespaces:
            for ns_item in exclude_namespaces:
                if ns_item in ns_string:
                    return False

        include_namespaces = self.include_dict.get("namespaces")
        if include_namespaces:
            for ns_item in include_namespaces:
                if ns_item in ns_string:
                    return True
            return False

        return True


def join_paths(base_dir, child_dir):
    if os.path.isabs(child_dir):
        return child_dir
    return os.path.join(base_dir, child_dir)


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
