#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Tuple, Any, Dict

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

    classes_info: List[ClassData] = get_classes_info(content, include_internals)
    for class_info in classes_info:
        class_name = class_info.name
        diagram_gen.add_class(class_name, allow_repeated=False)
        for base_name, base_access in class_info.bases:
            diagram_gen.add_connection(class_name, base_name, base_access, allow_repeated=False)

    diagram_gen.generate(out_path)
    _LOGGER.info("generating completed")


class ClassData:
    def __init__(self, name):
        self.name = name
        self.bases = []

    def add_base(self, base_name, base_access):
        self.bases.append((base_name, base_access))


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


def get_classes_info(content: LangContent, include_internals=False) -> List[ClassData]:
    ret_list = []
    for entry in content.content_objs.values():
        if entry.get_type() != "identifier_node":
            continue
        if not include_internals:
            if is_entry_language_internal(entry):
                continue
        info: ClassData = get_class_info(content, entry, include_internals=include_internals)
        if info is None:
            continue
        ret_list.append(info)
    return ret_list


def get_class_info(content: LangContent, identifier_entry: Entry, include_internals=False) -> ClassData:
    class_name = identifier_entry.get("strg")
    if not class_name:
        return None

    ancestors_dict = content.get_ancestors_dict()

    class_data_list = []

    parents_dict = content.get_parents_dict()
    entry_id = identifier_entry.get_id()
    parents_list = parents_dict.get(entry_id)
    for _parent_prop, parent_entry in parents_list:
        if parent_entry.get_type() != "type_decl":
            continue
        record_entry = parent_entry.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", parent_entry.get_id())
            continue
        if record_entry.get_type() != "record_type":
            continue

        entry_namespace_list = get_namespace_list(record_entry, ancestors_dict)
        if entry_namespace_list is None:
            continue

        entry_namespace_list.append(class_name)
        if not include_internals:
            if is_namespace_internal(entry_namespace_list):
                continue
        entry_name: str = "::".join(entry_namespace_list)

        data_dict: Dict[str, Any] = {}
        data_dict["type_entry"] = parent_entry
        data_dict["name"] = entry_name
        bases_data: List[Tuple[str, str]] = []

        bases = get_bases(record_entry, include_internals=include_internals)
        for base_entry, base_access in bases:
            base_namespace_list = get_namespace_list(base_entry, ancestors_dict)
            base_type_name = get_name_record_type(base_entry)
            base_namespace_list.append(base_type_name)
            if not include_internals:
                if is_namespace_internal(base_namespace_list):
                    continue
            base_name = "::".join(base_namespace_list)
            bases_data.append((base_access, base_name))

        data_dict["bases"] = bases_data
        class_data_list.append(data_dict)

    if not class_data_list:
        return None
    if len(class_data_list) > 1:
        return None

    class_data = class_data_list[0]
    type_entry = class_data["type_entry"]
    class_name = class_data["name"]
    bases_data = class_data["bases"]
    _LOGGER.info("inheritance: %s (%s) -> %a", class_name, type_entry.get_id(), bases_data)
    class_info = ClassData(class_name)
    for base_access, base_name in bases_data:
        class_info.add_base(base_name, base_access)

    return class_info


def get_name_record_type(entry: Entry):
    type_entry = entry.get("name")
    identifier_entry = type_entry.get("name")
    return identifier_entry.get("strg")


def get_namespace_list(record_entry: Entry, ancestors_dict) -> List[str]:
    ret_list = None
    entry_id = record_entry.get_id()
    lists = ancestors_dict.get(entry_id)
    for ancestors_list in lists:
        if len(ancestors_list) < 2:
            continue
        # ancestors_list = ancestors_list.copy()
        ancestor_data = ancestors_list[-1]
        abcestor_prop, ancestor = ancestor_data
        if abcestor_prop != "type":
            continue
        ancestor_data = ancestors_list[-2]
        abcestor_prop, ancestor = ancestor_data
        if ancestor.get_type() != "type_decl":
            continue
        if abcestor_prop != "dcls":
            continue

        namespace_list = []
        for _ancestor_prop, ancestor in ancestors_list:
            if ancestor.get_type() == "namespace_decl":
                ancestor_name = get_entry_name(ancestor)
                if ancestor_name == "[--unknown--]":
                    ancestor_name = "_anonymous_"
                if ancestor_name == "::":
                    ancestor_name = ""
                namespace_list.append(ancestor_name)
        if ret_list is None:
            ret_list = namespace_list
        else:
            if len(namespace_list) < len(ret_list):
                ret_list = namespace_list

    return ret_list


def get_bases(record_entry: Entry, include_internals=False):
    binf_entries = record_entry.get_sub_entries("binf")
    binf_entries_num = len(binf_entries)
    if binf_entries_num < 1:
        # happens e.g. for old-school enums
        return []

    if binf_entries_num > 1:
        raise RuntimeError(f"invalid number of 'binf' items: {binf_entries_num} for entry {record_entry.get_id()}")

    _prop, binf_item = binf_entries[0]

    binf_bases = binf_item.get("bases")
    if binf_bases is None:
        raise RuntimeError("missing required property 'bases'")
    binf_bases = int(binf_bases)
    if binf_bases < 1:
        return []

    binfo_access = binf_item.get("accs")
    if binfo_access is None:
        raise RuntimeError(f"missing required property 'accs' for entry {binf_item.get_id()}")

    ret_list = []
    found_items = set()

    internal_bases = 0
    subbinf_entries = binf_item.get_sub_entries("binf")
    for _prop, subitem in subbinf_entries:
        base_type = subitem.get("type")
        if not base_type or base_type.get_type() != "record_type":
            continue
        if not is_class_struct(base_type):
            continue
        if not include_internals and is_entry_language_internal(base_type):
            internal_bases += 1
            continue

        base_access = binfo_access
        base_spec = subitem.get("spec")
        if base_spec:
            base_access = f"{base_spec} {base_access}"

        found_id = (base_type.get_id(), base_access)
        if found_id in found_items:
            continue
        found_items.add(found_id)

        ret_list.append((base_type, base_access))

    if binf_bases > 1:
        flds_entries = record_entry.get_sub_entries("flds")
        for _prop, item in flds_entries:
            item_type = item.get_type()
            if item_type != "field_decl":
                # base class is defined as field_decl
                continue
            field_name = item.get("name")
            if field_name is not None:
                # base class definition does not have name
                continue
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
            if not include_internals and is_entry_language_internal(base_type):
                internal_bases += 1
                continue

            found_id = (base_type.get_id(), base_access)
            if found_id in found_items:
                continue
            found_items.add(found_id)

            ret_list.append((base_type, base_access))

    found_bases_num = len(ret_list) + internal_bases
    if found_bases_num != binf_bases:
        _LOGGER.info("found bases: %s", ret_list)
        raise RuntimeError(
            f"unable to find all bases for entry {record_entry.get_id()}, required {binf_bases} found {found_bases_num}"
        )

    return ret_list


def is_class_struct(entry: Entry):
    if entry.get("tag") == "struct":
        return True
    binf_data = entry.get("binf")
    return binf_data is not None
