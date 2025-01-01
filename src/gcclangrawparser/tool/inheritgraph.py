#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Dict

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
    is_namespace_internal,
)
from gcclangrawparser.langanalyze import (
    get_record_namespace_list,
    StructAnalyzer,
    get_function_args,
    get_function_ret,
)
from gcclangrawparser.diagram.classdiagram import ClassDiagramGenerator


_LOGGER = logging.getLogger(__name__)


FIELD_ACCESS_CONVERT_DICT = {"priv": "private", "prot": "protected", "pub": "public"}


def generate_inherit_graph(content: LangContent, out_path, include_internals=False):
    _LOGGER.info("generating inheritance graph to %s", out_path)
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_entries()

    inherit_data = InheritanceData(content, include_internals)
    classes_info = inherit_data.generate_data()

    diagram_gen = ClassDiagramGenerator(classes_info)
    diagram_gen.generate(out_path)

    _LOGGER.info("generating completed")


class InheritanceData:

    def __init__(self, content, include_internals=False):
        self.content = content
        self.include_internals = include_internals
        self.analyzer = StructAnalyzer(content, include_internals)

    def generate_data(self) -> Dict[str, ClassDiagramGenerator.ClassData]:
        ret_dict = {}
        dcls_list = self.content.get_entries("dcls")
        for dcls_entry in dcls_list:
            info_list = self.get_class_info(dcls_entry)
            if info_list:
                for info in info_list:
                    ret_dict[info.name] = info
        return ret_dict

    def get_class_info(self, dcls_entry: Entry) -> List[ClassDiagramGenerator.ClassData]:
        class_data_list = None

        if dcls_entry.get_type() == "type_decl":
            class_data_list = self._get_class_type_decl(dcls_entry)

        elif dcls_entry.get_type() == "template_decl":
            class_data_list = self._get_class_template_decl(dcls_entry)

        if class_data_list:
            class_names = [item.name for item in class_data_list]
            _LOGGER.info("found items %s for entry %s", class_names, dcls_entry.get_id())

        return class_data_list

    def _get_class_type_decl(self, type_decl: Entry) -> List[ClassDiagramGenerator.ClassData]:
        record_entry = type_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", type_decl.get_id())
            return None
        if record_entry.get_type() != "record_type":
            return None

        entry_name: str = self.analyzer.get_record_full_name(record_entry)
        if entry_name is None:
            return None

        class_data = ClassDiagramGenerator.ClassData()
        class_data.name = entry_name

        base_list = self._get_bases_list(record_entry)
        class_data.bases = base_list

        field_list = get_fields_list(record_entry, include_internals=self.include_internals)
        class_data.fields = field_list

        method_list = get_methods_list(entry_name, record_entry)
        class_data.methods = method_list

        class_data.generics = []

        return [class_data]

    def _get_class_template_decl(self, template_decl: Entry) -> List[ClassDiagramGenerator.ClassData]:
        record_entry = template_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", template_decl.get_id())
            return None
        if record_entry.get_type() != "record_type":
            return None

        entry_namespace_list = get_record_namespace_list(record_entry)
        if entry_namespace_list is None:
            return None
        if not self.include_internals:
            if is_namespace_internal(entry_namespace_list):
                return None
        entry_name: str = "::".join(entry_namespace_list)

        class_data = ClassDiagramGenerator.ClassData()
        class_data.name = entry_name

        base_list = self._get_bases_list(record_entry)
        class_data.bases = base_list

        field_list = get_fields_list(record_entry, include_internals=self.include_internals)
        class_data.fields = field_list

        method_list = get_methods_list(entry_name, record_entry)
        class_data.methods = method_list

        class_data.type = ClassDiagramGenerator.ClassType.TEMPLATE
        generics_list = get_template_parameters(template_decl)
        class_data.generics = generics_list

        ret_list = [class_data]

        ## read instances
        instantiations_entry = template_decl.get("inst")
        if instantiations_entry is None:
            # template without instantiations
            return ret_list

        insts_size = int(instantiations_entry.get("lngt"))
        for inst_index in range(0, insts_size):
            inst_index_str = str(inst_index)
            inst_entry = instantiations_entry.get(inst_index_str)
            valu_record_entry = inst_entry.get("valu")
            valu_type_entry = valu_record_entry.get("name")
            instance_info = self._get_class_type_decl(valu_type_entry)
            if instance_info is None:
                continue
            for inst_item in instance_info:
                base = ClassDiagramGenerator.ClassBase(entry_name, None)
                inst_item.bases.append(base)
            ret_list.extend(instance_info)

        return ret_list

    def _get_bases_list(self, record_entry: Entry):
        base_list = []
        record_entry_bases = self._get_bases(record_entry)
        for base_entry, base_access in record_entry_bases:
            base_name: str = self.analyzer.get_record_full_name(base_entry)
            if base_name is None:
                continue
            base = ClassDiagramGenerator.ClassBase(base_name, base_access)
            base_list.append(base)
        return base_list

    def _get_bases(self, record_entry: Entry):
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

        ret_list, internal_bases = get_bases_from_binf(binf_item, include_internals=self.include_internals)

        binfo_access = binf_item.get("accs")
        if binfo_access is None:
            raise RuntimeError(f"missing required property 'accs' for entry {binf_item.get_id()}")

        found_bases = set()
        for base_item in ret_list:
            base_type = base_item[0]
            base_name: str = self.analyzer.get_record_full_name(base_type)
            found_bases.add(base_name)

        if binf_bases > 1:
            class_name = get_entry_name(record_entry)

            record_spec = record_entry.get("spec")  # virt value
            virtual_bases_marker = False

            flds_entries = record_entry.get_sub_entries("flds")
            for _prop, item in flds_entries:
                item_type = item.get_type()

                if item_type == "type_decl":
                    if record_spec:
                        field_name = item.get("name")
                        field_name = get_entry_name(field_name)
                        if field_name is None:
                            continue
                        if field_name == class_name:
                            virtual_bases_marker = True
                        continue
                    # does not use virtual inheritance directly, so ignore other elements
                    break

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

                if not virtual_bases_marker:
                    base_spec = item.get("spec")
                    if base_spec:
                        base_access = base_spec + base_access
                else:
                    base_access = "virt ???"

                base_type = item.get("type")
                if base_type is None:
                    continue
                if base_type.get_type() != "record_type":
                    continue
                if not is_class_struct(base_type):
                    continue
                if not self.include_internals and is_entry_language_internal(base_type):
                    internal_bases += 1
                    continue

                base_type_name: str = self.analyzer.get_record_full_name(base_type)
                if base_type_name in found_bases:
                    continue
                found_bases.add(base_type_name)

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


def get_template_parameters(template_decl: Entry):
    params: Entry = template_decl.get("prms")
    if params is None:
        return []
    items_num = params.get("lngt")
    if items_num is None:
        return []
    items_num = str(items_num)

    ret_list = []
    params_list = get_vector_items(params)
    for param_item in params_list:
        valu: Entry = param_item.get("valu")
        if valu is None:
            return []

        sub_list = get_vector_items(valu)
        for sub_item in sub_list:
            if not isinstance(sub_item, Entry):
                continue
            sub_valu = sub_item.get("valu")
            if sub_valu is None:
                continue
            param_name = get_entry_name(sub_valu)
            if param_name is None:
                continue
            ret_list.append(param_name)
    return ret_list


def get_vector_items(vector: Entry):
    items_num = vector.get("lngt")
    if items_num is None:
        return []
    ret_list = []
    items_num = int(items_num)
    for index in range(0, items_num):
        param_item = vector.get(f"{index}")
        if param_item is None:
            _LOGGER.error("invalid data")
            return []
        ret_list.append(param_item)
    return ret_list


def get_name_record_type(entry: Entry):
    type_entry = entry.get("name")
    identifier_entry = type_entry.get("name")
    return identifier_entry.get("strg")


def get_type_namespace_list(type_decl: Entry, ancestors_dict):
    ident_entry = type_decl.get("name")
    if ident_entry is None:
        return None

    ident_name = ident_entry.get("strg")
    if ident_name is None:
        return None

    ret_list = None
    entry_id = ident_entry.get_id()
    lists = ancestors_dict.get(entry_id)
    for ancestors_list in lists:
        if len(ancestors_list) < 2:
            continue
        # ancestors_list = ancestors_list.copy()
        ancestor_data = ancestors_list[-1]
        abcestor_prop, ancestor = ancestor_data
        if abcestor_prop != "name":
            continue
        ancestor_data = ancestors_list[-2]
        abcestor_prop, ancestor = ancestor_data
        # if ancestor.get_type() != "type_decl":
        #     continue

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
        ret_list.append(ident_name)

    return ret_list


def get_bases_from_binf(binf_item: Entry, include_internals=True):
    binfo_access = binf_item.get("accs")
    if binfo_access is None:
        raise RuntimeError(f"missing required property 'accs' for entry {binf_item.get_id()}")

    ret_list = []
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

        ret_list.append((base_type, base_access))

    return ret_list, internal_bases


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


def get_methods_list(class_name, record_entry: Entry):
    method_list = []
    entry_methods = get_methods(record_entry)
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


def get_methods(record_entry: Entry):
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
            method_return = get_function_ret(method_type)

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
            args_list = get_function_args(item)
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


def is_class_struct(entry: Entry):
    if entry.get("tag") == "struct":
        return True
    binf_data = entry.get("binf")
    return binf_data is not None
