#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
)
from gcclangrawparser.plantuml import ClassDiagramGenerator


_LOGGER = logging.getLogger(__name__)


def generate_inherit_graph(content: LangContent, out_path, include_internals=False):
    _LOGGER.info("generating inheritance graph to %s", out_path)
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_chains()

    diagram_gen = ClassDiagramGenerator()

    ancestors_dict = content.get_ancestors_dict()

    # entry: Entry
    for entry in content.content_objs.values():
        if entry.get_type() != "record_type":
            continue
        if not is_class_struct(entry):
            continue
        if not include_internals:
            if is_entry_language_internal(entry):
                continue

        entry_namespace_list = get_namespace_list(entry, ancestors_dict)
        type_name = get_name_record_type(entry)
        entry_namespace_list.append(type_name)
        if not include_internals:
            if is_namespace_internal(entry_namespace_list):
                continue
        entry_name = "::".join(entry_namespace_list)

        bases = get_bases(entry, include_internals=include_internals)
        if not bases:
            diagram_gen.add_class(entry_name, allow_repeated=False)

        for base_entry, base_access in bases:
            base_namespace_list = get_namespace_list(base_entry, ancestors_dict)
            base_type_name = get_name_record_type(base_entry)
            base_namespace_list.append(base_type_name)
            if not include_internals:
                if is_namespace_internal(base_namespace_list):
                    continue
            base_name = "::".join(base_namespace_list)
            diagram_gen.add_connection(entry_name, base_name, base_access, allow_repeated=False)

    diagram_gen.generate(out_path)
    _LOGGER.info("generating completed")


def is_namespace_internal(namepace_list):
    copied_list = namepace_list.copy()
    copied_list = [value for value in copied_list if value != ""]  # remove empty elements
    if not copied_list:
        # empty list
        return False
    if copied_list[0] == "std":
        return True
    for name in namepace_list:
        if name.startswith("__"):
            return True
    return False


def get_name_record_type(entry: Entry):
    type_entry = entry.get("name")
    identifier_entry = type_entry.get("name")
    return identifier_entry.get("strg")


def get_namespace_list(entry: Entry, ancestors_dict) -> List[str]:
    ret_list = []
    entry_id = entry.get_id()
    ancestors_list = ancestors_dict.get(entry_id)
    for ancestor in ancestors_list:
        ancestor_entry = ancestor[0]
        if ancestor_entry.get_type() != "namespace_decl":
            continue
        ancestor_name = get_entry_name(ancestor_entry)
        if ancestor_name == "[--unknown--]":
            ancestor_name = "_anonymous_"
        if ancestor_name == "::":
            ancestor_name = ""
        ret_list.append(ancestor_name)
    return ret_list


def get_bases(entry: Entry, include_internals=False):
    ret_list = []
    sub_entries = entry.get_sub_entries("flds")
    for _prop, item in sub_entries:
        base_access = item.get("accs")
        if base_access is None:
            continue
        base_spec = item.get("spec")
        if base_spec:
            base_access = base_spec + base_access
        base_type = item.get("type")
        if base_type is None:
            continue
        if base_type.get_type() != "record_type":
            continue
        if not is_class_struct(base_type):
            continue

        if not include_internals:
            if is_entry_language_internal(base_type):
                continue

        ret_list.append((base_type, base_access))
    return ret_list


def is_class_struct(entry: Entry):
    binf_data = entry.get("binf")
    return binf_data is not None
