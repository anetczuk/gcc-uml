#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Dict, Any

from gccuml.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
    get_number_entry_value,
    get_template_parameters,
    get_type_entry_name,
    get_function_ret,
    get_function_args,
    get_decl_namespace_list,
)
from gccuml.langanalyze import (
    StructAnalyzer,
)
from gccuml.diagram.plantuml.classdiagram import ClassDiagramGenerator
from gccuml.langparser import parse_raw
from gccuml.configyaml import Filter
from gccuml.expressionanalyze import ScopeAnalysis, EntryExpression


_LOGGER = logging.getLogger(__name__)


FIELD_ACCESS_CONVERT_DICT = {"priv": "private", "prot": "protected", "pub": "public"}


def generate_inherit_graph_config(config: Dict[Any, Any]):
    input_files = config.get("inputfiles")
    if not input_files:
        raise RuntimeError("no input files given")
    if len(input_files) > 1:
        raise RuntimeError(f"multiple input files not supported: {input_files}")
    raw_file_path = input_files[0]
    _LOGGER.info("parsing input file %s", raw_file_path)
    reduce_paths = config.get("reducepaths", False)
    content: LangContent = parse_raw(raw_file_path, reduce_paths)
    if content is None:
        raise RuntimeError(f"unable to parse {raw_file_path}")
    out_path = config.get("outpath")
    if not out_path:
        raise RuntimeError("no output path given")
    item_filter: Filter = Filter.create(config)
    generate_inherit_graph(content, out_path, item_filter=item_filter)


def generate_inherit_graph(content: LangContent, out_path, include_internals=False, item_filter: Filter = None):
    _LOGGER.info("generating inheritance graph to %s", out_path)
    if item_filter is None:
        item_filter = Filter()
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_entries()

    inherit_data = InheritanceData(content, include_internals)
    classes_info = inherit_data.generate_data()

    diagram_gen = ClassDiagramGenerator(classes_info)
    diagram_gen.generate(out_path)

    _LOGGER.info("generating completed")


class InheritanceData:

    def __init__(self, content: LangContent, include_internals: bool = False):
        self.content: LangContent = content
        self.include_internals: bool = include_internals
        self.analyzer: StructAnalyzer = StructAnalyzer(content, include_internals)

    def generate_data(self) -> Dict[str, ClassDiagramGenerator.ClassData]:
        ret_dict: Dict[str, ClassDiagramGenerator.ClassData] = {}

        ## add types
        type_decl_list = self.content.get_entries_by_type("type_decl")
        for type_decl_entry in type_decl_list:
            class_data_list = self._get_class_type_decl(type_decl_entry)
            if not class_data_list:
                continue
            class_names = [item.get_name() for item in class_data_list]
            _LOGGER.info("found type %s for entry %s", class_names, type_decl_entry.get_id())
            for info in class_data_list:
                ret_dict[info.item_id] = info

        ## add templates
        type_decl_list = self.content.get_entries_by_type("template_decl")
        for type_decl_entry in type_decl_list:
            class_data_list = self._get_class_template_decl(type_decl_entry)
            if not class_data_list:
                continue
            class_names = [item.get_name() for item in class_data_list]
            _LOGGER.info("found template %s for entry %s", class_names, type_decl_entry.get_id())
            for info in class_data_list:
                ret_dict[info.item_id] = info

        ## adding static fields
        var_decl_list = self.content.get_entries_by_type("var_decl")
        for var_decl_entry in var_decl_list:
            var_scope = var_decl_entry.get("scpe")
            if var_scope is None:
                continue
            scope_type = var_scope.get_type()
            if scope_type != "record_type":
                continue
            scope_name: str = self.analyzer.get_record_full_name(var_scope)
            if scope_name is None:
                continue
            record_id = var_scope.get_id()
            class_data: ClassDiagramGenerator.ClassData = ret_dict.get(record_id)
            if class_data is None:
                _LOGGER.warning("unable to get class data for name '%s'", scope_name)
                continue
            field_data = self.get_field_data(var_decl_entry, include_internals=True)
            if field_data is None:
                continue
            field_name, field_type, field_access, is_static, bitfield_size, init_value = field_data
            if class_data.has_field(field_name):
                continue

            field_access = FIELD_ACCESS_CONVERT_DICT[field_access]
            field = ClassDiagramGenerator.ClassField(
                field_name, field_type, field_access, is_static, bitfield_size, init_value
            )
            class_data.fields.insert(0, field)
            _LOGGER.info("added static field '%s' of type '%s' to class '%s'", field_name, field_type, scope_name)

        # ## add inner types
        # scpe_list = self.content.get_entries_with_prop("scpe")
        # for scpe_item in scpe_list:
        #     owner_entry = scpe_item.get("scpe")
        #     owner_id = owner_entry.get_id()
        #     owner_class_data: ClassDiagramGenerator.ClassData = ret_dict.get(owner_id)
        #     if owner_class_data is None:
        #         continue
        #     scpe_type_entry = scpe_item.get("type")
        #     if scpe_type_entry is None:
        #         continue
        #     type_id = scpe_type_entry.get_id()
        #     if owner_class_data.has_inner(type_id):
        #         continue
        #     if self._is_inner_type(owner_entry, scpe_item) == False:
        #         continue
        #     entry_name: str = self.analyzer.get_record_full_name(scpe_item)
        #     sub_type = ClassDiagramGenerator.TypeAlias(type_id, entry_name)
        #     owner_class_data.inner_types.append(sub_type)

        return ret_dict

    # def get_class_info(self, dcls_entry: Entry) -> List[ClassDiagramGenerator.ClassData]:
    #     class_data_list = None
    #
    #     if dcls_entry.get_type() == "type_decl":
    #         class_data_list = self._get_class_type_decl(dcls_entry)
    #
    #     elif dcls_entry.get_type() == "template_decl":
    #         class_data_list = self._get_class_template_decl(dcls_entry)
    #
    #     if class_data_list:
    #         class_names = [item.name for item in class_data_list]
    #         _LOGGER.info("found items %s for entry %s", class_names, dcls_entry.get_id())
    #
    #     return class_data_list

    def _get_class_type_decl(self, type_decl: Entry) -> List[ClassDiagramGenerator.ClassData]:
        record_entry = type_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", type_decl.get_id())
            return None

        entry_name: str = self.analyzer.get_record_full_name(record_entry)
        if entry_name is None:
            return None

        alias_type_entry = self.get_aliased_type(record_entry)  ## required "unql" field
        alias_name: str = None

        if record_entry.get_type() == "typename_type":
            if not alias_type_entry:
                ## seems to be inner type
                return None

            ## alias
            entry_id = record_entry.get_id()
            class_data = ClassDiagramGenerator.ClassData(entry_id)
            class_data.name = entry_name
            alias_id = alias_type_entry.get_id()
            alias_name = self.analyzer.get_record_full_name(alias_type_entry)
            class_data.aliasof = ClassDiagramGenerator.TypeAlias(alias_id, alias_name)
            return [class_data]

        if record_entry.get_type() != "record_type":
            return None

        type_note = type_decl.get("note")
        if type_note is not None and type_note == "artificial":
            unql_entry = record_entry.get("unql")
            if unql_entry:
                return None

        entry_id = record_entry.get_id()
        class_data = ClassDiagramGenerator.ClassData(entry_id)
        class_data.name = entry_name

        if alias_type_entry:
            ## alias
            alias_id = alias_type_entry.get_id()
            alias_name = self.analyzer.get_record_full_name(alias_type_entry)
            class_data.aliasof = ClassDiagramGenerator.TypeAlias(alias_id, alias_name)
            return [class_data]

        ## normal type
        base_list = self._get_bases_list(record_entry)
        class_data.bases = base_list

        field_list = self._get_fields_list(record_entry, include_internals=self.include_internals)
        class_data.fields = field_list

        method_list = get_methods_list(entry_name, record_entry)
        class_data.methods = method_list

        class_data.generics = []
        class_data.inner_types = self._get_inner_types(record_entry)

        return [class_data]

    def _get_class_template_decl(self, template_decl: Entry) -> List[ClassDiagramGenerator.ClassData]:
        record_entry = template_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", template_decl.get_id())
            return None
        if record_entry.get_type() not in ("record_type", "typename_type"):
            return None

        # entry_namespace_list = get_record_namespace_list(record_entry)
        # if entry_namespace_list is None:
        #     return None
        # if not self.include_internals:
        #     if is_namespace_internal(entry_namespace_list):
        #         return None
        # entry_name: str = "::".join(entry_namespace_list)
        entry_name: str = self.analyzer.get_record_full_name(record_entry)

        entry_id = record_entry.get_id()
        class_data = ClassDiagramGenerator.ClassData(entry_id)
        class_data.name = entry_name

        alias_type_entry = self.get_aliased_type(record_entry)
        if alias_type_entry:
            ## alias
            alias_id = alias_type_entry.get_id()
            alias_name: str = self.analyzer.get_record_full_name(alias_type_entry)
            class_data.aliasof = ClassDiagramGenerator.TypeAlias(alias_id, alias_name)

        ## normal type
        base_list = self._get_bases_list(record_entry)
        class_data.bases = base_list

        field_list = self._get_fields_list(record_entry, include_internals=self.include_internals)
        for item in field_list:
            # it is unable to detect if template field is marked as static
            item.static = False
        class_data.fields = field_list

        method_list = get_methods_list(entry_name, record_entry)
        class_data.methods = method_list

        class_data.type = ClassDiagramGenerator.ClassType.TEMPLATE
        generics_list = get_template_parameters(template_decl)
        class_data.generics = generics_list

        class_data.inner_types = self._get_inner_types(record_entry)

        ret_list = [class_data]

        ## read instances
        instantiations_entry = template_decl.get("inst")
        if instantiations_entry is None:
            # template without instantiations
            return ret_list

        ## read instances
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
                base = ClassDiagramGenerator.ClassBase(entry_id, entry_name, None)
                inst_item.bases.append(base)
            ret_list.extend(instance_info)

        return ret_list

    def _get_inner_types(self, record_entry):
        ret_types = []
        flds_entries = record_entry.get_sub_entries("flds")
        for _prop, flds_entry in flds_entries:
            if self._is_inner_type(record_entry, flds_entry) is False:
                continue
            ## inner type found
            item_type = flds_entry.get_type()
            if item_type in ("type_decl", "template_decl"):
                fld_type_entry = flds_entry.get("type")
                field_id = fld_type_entry.get_id()
                field_name: str = self.analyzer.get_record_full_name(flds_entry)
                sub_type = ClassDiagramGenerator.TypeAlias(field_id, field_name)
                ret_types.append(sub_type)
        return ret_types

    def _is_inner_type(self, class_entry, fld_entry):
        class_name_list = get_decl_namespace_list(class_entry)
        field_name_list = get_decl_namespace_list(fld_entry)
        # class_name = get_type_entry_name(class_entry)
        # field_name = get_type_entry_name(fld_entry)
        if not field_name_list or not class_name_list:
            # proper field must have name
            return False
        if field_name_list[-1] == class_name_list[-1]:
            ## there cannot be any member of name the same as class name (it is used for internal representation only)
            return False
        return True

    def _get_bases_list(self, record_entry: Entry):
        base_list = []
        record_entry_bases = self._get_bases(record_entry)
        for base_entry, base_access in record_entry_bases:
            base_name: str = self.analyzer.get_record_full_name(base_entry)
            if base_name is None:
                continue
            entry_id = base_entry.get_id()
            base = ClassDiagramGenerator.ClassBase(entry_id, base_name, base_access)
            base_list.append(base)
        return base_list

    def _get_bases(self, record_entry: Entry):
        binf_entries = record_entry.get_list("binf")
        binf_entries_num = len(binf_entries)
        if binf_entries_num < 1:
            # happens e.g. for old-school enums
            return []

        if binf_entries_num > 1:
            raise RuntimeError(f"invalid number of 'binf' items: {binf_entries_num} for entry {record_entry.get_id()}")

        binf_item = binf_entries[0]
        binfo_access_list = binf_item.get_list("accs")
        subbinfo_list = binf_item.get_list("binf")

        binf_bases = binf_item.get("bases")
        if binf_bases is None:
            raise RuntimeError("missing required property 'bases' for entry {binf_item.get_id()}")
        binf_bases = int(binf_bases)

        if len(binfo_access_list) != len(subbinfo_list):
            raise RuntimeError(f"invalid number of 'binf' and 'accs' items for entry {binf_item.get_id()}")

        ret_list = []
        for base_index in range(0, binf_bases):
            base_access = binfo_access_list[base_index]
            base_info = subbinfo_list[base_index]
            base_spec = base_info.get("spec")
            base_type = base_info.get("type")
            if "virt" == base_spec:
                base_access = "virt " + base_access
            ret_list.append((base_type, base_access))

        return ret_list

    def _get_fields_list(self, record_entry: Entry, include_internals=False) -> List[ClassDiagramGenerator.ClassField]:
        field_list = []
        entry_fields = self.get_fields(record_entry, include_internals=include_internals)

        ## added later
        # vtable_var_decl = find_class_vtable_var_decl(self.content, record_entry)
        # if vtable_var_decl is not None:
        #     field_data = get_field_data(vtable_var_decl, include_internals)
        #     if field_data is not None:
        #         entry_fields.insert(0, field_data)

        for item in entry_fields:
            field_name, field_type, field_access, field_static, bitfield_size, init_val = item
            access = FIELD_ACCESS_CONVERT_DICT[field_access]
            field = ClassDiagramGenerator.ClassField(
                field_name, field_type, access, field_static, bitfield_size, init_val
            )
            field_list.append(field)

        return field_list

    def get_fields(self, record_entry: Entry, include_internals=False):
        ret_list = []

        flds_entries = record_entry.get_sub_entries("flds")
        for _prop, item in flds_entries:
            field_data = self.get_field_data(item, include_internals)
            if field_data is None:
                continue
            ret_list.append(field_data)

        return ret_list

    def get_field_data(self, flds_item: Entry, include_internals=False):
        item_type = flds_item.get_type()
        if item_type not in ("field_decl", "var_decl"):
            # field is defined as field_decl
            return None
        field_name = flds_item.get("name")
        field_name = get_entry_name(field_name)
        if field_name is None:
            # proper field must have name
            return None
        # if field_name.startswith("_vptr."):
        #     # ignore vtable
        #     return None
        field_access = flds_item.get("accs")
        if field_access is None:
            return None

        bitfield_size = None
        field_bitfield = flds_item.get("bitfield")
        if field_bitfield and field_bitfield != "0":
            field_size_entry = flds_item.get("size")
            if field_size_entry:
                bitfield_size = get_number_entry_value(field_size_entry)

        field_type = flds_item.get("type")
        field_type = get_type_entry_name(field_type)
        # field_type = get_entry_name(field_type)
        if field_type is None:
            if bitfield_size:
                field_type = "???"
            else:
                return None
        if not include_internals and is_entry_language_internal(field_type):
            return None

        ## check mutable
        field_spec = flds_item.get_list("spec")
        if field_spec:
            if "mutable" in field_spec:
                field_type = f"mutable {field_type}"
            else:
                _LOGGER.warning("entry %s unknown 'spec' value: %s", flds_item.get_id(), field_spec)

        bpos_entry = flds_item.get("bpos")
        is_static = bpos_entry is None

        analysis = ScopeAnalysis(self.content)
        var_expr: EntryExpression = analysis.handle_var(flds_item)
        init_value = None
        if "=" in var_expr.expression:
            first_pos = var_expr.expression.index("=")
            init_value = var_expr.expression[first_pos + 1 :]
            init_value = init_value.strip()

        return (field_name, field_type, field_access, is_static, bitfield_size, init_value)

    def get_aliased_type(self, record_entry: Entry) -> Entry:
        alias_type_entry = record_entry.get("unql")
        if alias_type_entry is None:
            return None
        return alias_type_entry


def get_name_record_type(entry: Entry):
    type_entry = entry.get("name")
    identifier_entry = type_entry.get("name")
    return identifier_entry.get("strg")


def get_methods_list(class_name, record_entry: Entry):
    method_list = []
    entry_methods = get_methods(record_entry)
    for item in entry_methods:
        meth_name, meth_type, meth_mod, meth_access, meth_args, meth_static = item
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
        method = ClassDiagramGenerator.ClassMethod(meth_name, meth_type, meth_mod, access, args_list, meth_static)
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
        method_type_type = method_type.get_type()
        if method_type_type not in ("method_type", "function_type"):
            # function is defined as method_type
            continue

        method_note_list = item.get_list("note")
        method_return = ""
        if "constructor" not in method_note_list and "destructor" not in method_note_list:
            method_return = get_function_ret(method_type)
            if method_return is None:
                method_return = ""

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
        method_spec = item.get_list("spec")
        method_virtual = False
        if method_spec:
            if "virt" in method_spec:
                method_virtual = True
                method_mods.append("virtual")
            else:
                _LOGGER.warning("entry %s unknown 'spec' value: %s", item.get_id(), method_spec)

        method_body = item.get_list("body")
        if "undefined" in method_body and len(method_body) == 1:
            if "constructor" in method_note_list or "destructor" in method_note_list:
                method_mods.append("default")
            else:
                if method_virtual:
                    method_mods.append("purevirt")

        method_mods_str = " ".join(method_mods)

        args_list = []
        if "destructor" not in method_note_list:
            ## destructor does not have any parameters
            args_list = get_function_args(item)

        is_static = method_type_type == "function_type"

        ret_list.append((method_name, method_return, method_mods_str, method_access, args_list, is_static))

    return ret_list


def get_method_name(function_decl: Entry, class_name: str) -> str:
    method_name = function_decl.get("name")
    method_name = get_entry_name(method_name)
    if method_name is None:
        # proper field must have name
        return None

    method_note_list = function_decl.get_list("note")
    if "constructor" in method_note_list:
        if method_name == "__ct":
            # does not allow to detect "default"
            return None
        if method_name == "__ct_comp":
            return None
        if method_name == "__ct_base":
            # allows to detect "default"
            method_name = class_name
        return method_name
    if "destructor" in method_note_list:
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
    this_arg_note_list = parm_decl_entry.get_list("note")
    if not this_arg_note_list:
        return ""
    if "artificial" not in this_arg_note_list:
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
