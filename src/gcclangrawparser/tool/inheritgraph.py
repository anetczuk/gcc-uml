#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Any, Dict

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
)
from gcclangrawparser.plantuml import ClassDiagramGenerator


_LOGGER = logging.getLogger(__name__)


FIELD_ACCESS_CONVERT_DICT = {"priv": "private", "prot": "protected", "pub": "public"}


def generate_inherit_graph(content: LangContent, out_path, include_internals=False):
    _LOGGER.info("generating inheritance graph to %s", out_path)
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_chains()

    classes_info = get_classes_info(content, include_internals)
    diagram_gen = ClassDiagramGenerator(classes_info)

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


def get_classes_info(content: LangContent, include_internals=False) -> Dict[str, ClassDiagramGenerator.ClassData]:
    ret_dict = {}
    for entry in content.content_objs.values():
        if entry.get_type() != "identifier_node":
            continue
        if not include_internals:
            if is_entry_language_internal(entry):
                continue
        info = get_class_info(content, entry, include_internals=include_internals)
        if info is None:
            continue
        ret_dict[info.name] = info
    return ret_dict


def get_class_info(
    content: LangContent, identifier_entry: Entry, include_internals=False
) -> ClassDiagramGenerator.ClassData:
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
        if not include_internals:
            if is_namespace_internal(entry_namespace_list):
                continue
        entry_name: str = "::".join(entry_namespace_list)

        data_dict: Dict[str, Any] = {}
        data_dict["type_entry"] = parent_entry
        data_dict["name"] = entry_name

        base_list = get_bases_list(record_entry, ancestors_dict, include_internals=include_internals)
        data_dict["bases"] = base_list

        field_list = get_fields_list(record_entry, include_internals=include_internals)
        data_dict["fields"] = field_list

        method_list = get_methods_list(entry_name, record_entry, ancestors_dict)
        data_dict["methods"] = method_list

        class_data_list.append(data_dict)

    if not class_data_list:
        return None
    # if len(class_data_list) > 1:
    #     return None

    raw_data = class_data_list[0]

    class_data = ClassDiagramGenerator.ClassData()
    class_data.name = raw_data["name"]
    class_data.bases = raw_data["bases"]
    class_data.fields = raw_data["fields"]
    class_data.methods = raw_data["methods"]

    return class_data


def get_name_record_type(entry: Entry):
    type_entry = entry.get("name")
    identifier_entry = type_entry.get("name")
    return identifier_entry.get("strg")


def get_full_name(entry: Entry, ancestors_dict) -> str:
    if entry.get_type() == "record_type":
        ns_list = get_namespace_list(entry, ancestors_dict)
        return "::".join(ns_list)
    return get_entry_name(entry)


def get_namespace_list(record_entry: Entry, ancestors_dict) -> List[str]:
    unql_entry = record_entry.get("unql")
    if unql_entry is not None:
        record_entry = unql_entry

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

    if ret_list is not None:
        base_type_name = get_name_record_type(record_entry)
        ret_list.append(base_type_name)

    return ret_list


def get_bases_list(record_entry: Entry, ancestors_dict, include_internals=False):
    base_list = []
    entry_bases = get_bases(record_entry, include_internals=include_internals)
    for base_entry, base_access in entry_bases:
        base_namespace_list = get_namespace_list(base_entry, ancestors_dict)
        if not include_internals:
            if is_namespace_internal(base_namespace_list):
                continue
        base_name = "::".join(base_namespace_list)
        base = ClassDiagramGenerator.ClassBase(base_name, base_access)
        base_list.append(base)
    return base_list


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
        _LOGGER.error(
            "unable to find all bases for entry %s, required %s found %s",
            record_entry.get_id(),
            binf_bases,
            found_bases_num,
        )

    return ret_list


def get_fields_list(record_entry: Entry, include_internals=False):
    field_list = []
    entry_fields = get_fields(record_entry, include_internals=include_internals)
    for item in entry_fields:
        field_name, field_type, field_access = item
        access = FIELD_ACCESS_CONVERT_DICT[field_access]
        field = ClassDiagramGenerator.ClassField(field_name, field_type, access)
        field_list.append(field)
    return field_list


def get_fields(record_entry: Entry, include_internals=False):
    ret_list = []

    flds_entries = record_entry.get_sub_entries("flds")
    for _prop, item in flds_entries:
        item_type = item.get_type()
        if item_type != "field_decl":
            # field is defined as field_decl
            continue
        field_name = item.get("name")
        field_name = get_entry_name(field_name)
        if field_name is None:
            # proper field must have name
            continue
        if field_name.startswith("_vptr."):
            # ignore vtable
            continue
        field_access = item.get("accs")
        if field_access is None:
            continue

        field_type = item.get("type")
        field_type = get_entry_name(field_type)
        if field_type is None:
            continue
        if not include_internals and is_entry_language_internal(field_type):
            continue

        ret_list.append((field_name, field_type, field_access))

    return ret_list


def get_methods_list(class_name, record_entry: Entry, ancestors_dict):
    method_list = []
    entry_methods = get_methods(record_entry, ancestors_dict)
    for item in entry_methods:
        meth_name, meth_type, meth_mod, meth_access, meth_args = item
        access = FIELD_ACCESS_CONVERT_DICT[meth_access]
        args_list = []
        for arg_item in meth_args:
            arg_name, arg_type = arg_item
            if arg_name == "this":
                if "const" in meth_mod:
                    if arg_type == f"{class_name} const * const":
                        continue
                else:
                    if arg_type == f"{class_name} * const":
                        continue
            arg = ClassDiagramGenerator.FunctionArg(arg_name, arg_type)
            args_list.append(arg)
        method = ClassDiagramGenerator.ClassMethod(meth_name, meth_type, meth_mod, access, args_list)
        method_list.append(method)
    return method_list


def get_methods(record_entry: Entry, ancestors_dict):
    ret_list = []

    class_name = get_entry_name(record_entry)

    flds_entries = record_entry.get_sub_entries("flds")
    for _prop, item in flds_entries:
        if item.get_type() != "function_decl":
            # base class is defined as field_decl
            continue
        method_name = get_method_name(item, class_name)
        if method_name is None:
            # proper field must have name
            continue

        method_access = item.get("accs")
        if method_access is None:
            continue

        method_type = item.get("type")
        if method_type is None:
            continue
        if method_type.get_type() != "method_type":
            # function is defined as method_type
            continue

        method_return = ""
        method_note = item.get("note")
        if method_note not in ("constructor", "destructor"):
            method_retn = method_type.get("retn")
            if method_retn is None:
                continue
            ret_type, ret_mod = get_type_name(method_retn, ancestors_dict)
            method_return = ret_type
            if ret_mod:
                method_return = f"{method_return} {ret_mod}"

            method_mod = method_retn.get("qual")
            if method_mod is not None:
                method_mod = get_entry_name(method_mod)
                if method_mod == "c":
                    method_return = f"{method_return} const"

        method_mods: List[str] = []

        method_args = item.get_sub_entries("args")
        if not method_args:
            continue

        ## determine "constness" of method
        this_arg = method_args[0]
        this_arg = this_arg[1]
        this_mod = get_this_modifier(this_arg)
        if this_mod:
            method_mods.append(this_mod)

        ## check if method is virtual
        method_spec = item.get("spec")
        method_virtual = False
        if method_spec is not None:
            if method_spec == "virt":
                method_virtual = True
                method_mods.append("virtual")
            else:
                _LOGGER.warning("entry %s unknown 'spec' value: %s", item.get_id(), method_spec)

        method_body = item.get("body")
        if method_body == "undefined":
            if method_note in ("constructor", "destructor"):
                method_mods.append("default")
            else:
                if method_virtual:
                    method_mods.append("purevirt")

        method_mods_str = " ".join(method_mods)

        args_list = []
        if method_note != "destructor":
            ## destructor does not have any parameters
            for _arg_prop, arg_entry in method_args:
                arg_name = arg_entry.get("name")
                arg_name = get_entry_name(arg_name)
                arg_type_entry = arg_entry.get("type")
                arg_type, arg_mod = get_type_name(arg_type_entry, ancestors_dict)
                arg_type_full = arg_type
                if arg_mod:
                    arg_type_full = f"{arg_type_full} {arg_mod}"
                args_list.append([arg_name, arg_type_full])

        ret_list.append((method_name, method_return, method_mods_str, method_access, args_list))

    return ret_list


def get_method_name(function_decl: Entry, class_name: str) -> str:
    method_name = function_decl.get("name")
    method_name = get_entry_name(method_name)
    if method_name is None:
        # proper field must have name
        return None

    method_note = function_decl.get("note")
    if method_note == "constructor":
        if method_name == "__ct":
            # does not allow to detect "default"
            return None
        if method_name == "__ct_comp":
            return None
        if method_name == "__ct_base":
            # allows to detect "default"
            method_name = class_name
        return method_name
    if method_note == "destructor":
        if method_name == "__dt":
            # does not allow to detect "default"
            return None
        if method_name == "__dt_base":
            return None
        if method_name == "__dt_comp":
            # allows to detect "default"
            method_name = f"~{class_name}"
        elif method_name == "__dt_del":
            # generated in case of virtual destructor
            return None
    return method_name


def get_this_modifier(parm_decl_entry: Entry):
    this_arg_name = parm_decl_entry.get("name")
    this_arg_name = get_entry_name(this_arg_name)
    if this_arg_name != "this":
        return ""
    this_arg_note = parm_decl_entry.get("note")
    if not this_arg_note:
        return ""
    if this_arg_note != "artificial":
        return ""

    arg_type = parm_decl_entry.get("type")
    if arg_type.get_type() != "pointer_type":
        return ""
    ptd = arg_type.get("ptd")
    ptd_qual = ptd.get("qual")
    if ptd_qual == "c":
        return "const"
    return ""


def get_type_name(type_entry: Entry, ancestors_dict):
    parm_mod = None
    arg_qual = type_entry.get("qual")
    if arg_qual == "c":
        parm_mod = "const"

    if type_entry.get_type() == "pointer_type":
        ptd = type_entry.get("ptd")
        ptd_name = get_full_name(ptd, ancestors_dict)
        ptd_qual = ptd.get("qual")
        if ptd_qual == "c":
            ptd_name += " const"
        ptd_name += " *"
        return (ptd_name, parm_mod)

    if type_entry.get_type() == "reference_type":
        refd = type_entry.get("refd")
        refd_name = get_full_name(refd, ancestors_dict)
        refd_qual = refd.get("qual")
        if refd_qual == "c":
            refd_name += " const"
        refd_name += " &"
        return (refd_name, parm_mod)

    param_name = get_entry_name(type_entry)
    return (param_name, parm_mod)


def is_class_struct(entry: Entry):
    if entry.get("tag") == "struct":
        return True
    binf_data = entry.get("binf")
    return binf_data is not None
