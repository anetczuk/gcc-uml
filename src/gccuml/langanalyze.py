#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging

from gccuml.langcontent import (
    Entry,
    get_entry_name,
    is_namespace_internal,
    get_record_namespace_list,
    get_type_name_mod,
    get_decl_namespace_list,
    get_entry_repr,
    LangContent,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


class StructAnalyzer:

    def __init__(self, content, include_internals=False):
        self.content = content
        self.include_internals = include_internals
        self.template_instances_dict = None

    # def generate_data(self) -> Dict[str, StructData]:
    #     ret_dict = {}
    #     dcls_list = self.content.get_entries("dcls")
    #     self._process_decls(dcls_list)
    #     for dcls_entry in dcls_list:
    #         info_list = self.get_class_info(dcls_entry)
    #         if info_list:
    #             for info in info_list:
    #                 ret_dict[info.name] = info
    #     return ret_dict

    def get_template_defs(self):
        if self.template_instances_dict is None:
            dcls_list = self.content.get_entries("dcls")
            self._process_decls(dcls_list)
        return self.template_instances_dict

    def _process_decls(self, dcls_list):
        self.template_instances_dict = {}
        for dcls_entry in dcls_list:
            # if dcls_entry.get_type() == "type_decl":
            #     type_namespace = get_type_namespace_list(dcls_entry)
            #     type_full_name = "::".join(type_namespace)
            #     classes_dict[type_full_name] = dcls_entry
            #     continue
            if dcls_entry.get_type() == "template_decl":
                instantiations_entry = dcls_entry.get("inst")
                if instantiations_entry is None:
                    ## function template - skip
                    continue
                insts_size = int(instantiations_entry.get("lngt"))
                for inst_index in range(0, insts_size):
                    inst_index_str = str(inst_index)
                    inst_entry = instantiations_entry.get(inst_index_str)
                    valu_record_entry = inst_entry.get("valu")
                    valu_record_id = valu_record_entry.get_id()
                    purp_entry = inst_entry.get("purp")
                    purp_type_list = []
                    purp_size = int(purp_entry.get("lngt"))
                    for purp_index in range(0, purp_size):
                        purp_index_str = str(purp_index)
                        purp_type_entry = purp_entry.get(purp_index_str)
                        purp_type_name = get_entry_name(purp_type_entry)
                        purp_type_list.append(purp_type_name)
                    self.template_instances_dict[valu_record_id] = purp_type_list

    def get_record_full_name(self, record_decl: Entry):
        entry_namespace_list = get_record_namespace_list(record_decl)
        if entry_namespace_list is None:
            return None
        if not self.include_internals:
            if is_namespace_internal(entry_namespace_list):
                return None
        entry_name: str = "::".join(entry_namespace_list)

        template_instances_dict = self.get_template_defs()
        record_entry_id = record_decl.get_id()
        template_params = template_instances_dict.get(record_entry_id)
        if template_params is not None:
            template_params_str = ", ".join(template_params)
            entry_name = f"{entry_name}<{template_params_str}>"
        return entry_name


def get_function_full_name(function_decl: Entry):
    if function_decl is None:
        return None
    if function_decl.get_type() != "function_decl":
        raise RuntimeError("case never occurred")

    scope = function_decl.get("scpe")
    if scope is None:
        raise RuntimeError("case never occurred")

    if scope.get_type() != "record_type":
        ## regular function
        name_prefix = get_decl_namespace_list(function_decl)
        return "::".join(name_prefix)

    ## class method
    name_entry = function_decl.get("name")
    method_name = get_entry_name(name_entry)
    if method_name is None:
        # proper field must have name
        return None

    method_note_list = function_decl.get_list("note")
    if "constructor" in method_note_list:
        method_name = get_entry_name(scope)
    elif "destructor" in method_note_list:
        class_name = get_entry_name(scope)
        method_name = f"~{class_name}"

    name_prefix = get_decl_namespace_list(function_decl)
    name_prefix[-1] = method_name
    return "::".join(name_prefix)


def get_function_name(function_decl: Entry):
    if function_decl is None:
        return None
    if function_decl.get_type() != "function_decl":
        raise RuntimeError("case never occurred")

    scope = function_decl.get("scpe")
    if scope is None:
        raise RuntimeError("case never occurred")

    if scope.get_type() != "record_type":
        ## regular function
        name_prefix = get_decl_namespace_list(function_decl)
        return "::".join(name_prefix)

    ## class method
    name_entry = function_decl.get("name")
    method_name = get_entry_name(name_entry)
    if method_name is None:
        # proper field must have name
        return None

    method_note_list = function_decl.get_list("note")
    if "constructor" in method_note_list:
        method_name = get_entry_name(scope)
    elif "destructor" in method_note_list:
        class_name = get_entry_name(scope)
        method_name = f"~{class_name}"

    name_prefix = get_decl_namespace_list(function_decl)
    name_prefix[-1] = method_name
    return "::".join(name_prefix)


def get_function_args(function_decl: Entry):
    func_args = function_decl.get_sub_entries("args")
    if not func_args:
        return []

    is_meth = is_method(function_decl)

    args_list = []
    for arg_index, arg_data in enumerate(func_args):
        _arg_prop, arg_entry = arg_data
        arg_name = arg_entry.get("name")
        arg_name = get_entry_name(arg_name)
        if arg_index == 0 and is_meth and arg_name == "this":
            # skip this parameter
            continue
        arg_type_entry = arg_entry.get("type")
        arg_type, arg_mod = get_type_name_mod(arg_type_entry)
        arg_type_full = arg_type
        if arg_mod:
            arg_type_full = f"{arg_type_full} {arg_mod}"
        args_list.append([arg_name, arg_type_full])
    return args_list


def get_function_ret(function_type: Entry):
    function_retn = function_type.get("retn")
    if function_retn is None:
        return None
    ret_type, ret_mod = get_type_name_mod(function_retn)
    function_return = ret_type
    if ret_mod:
        function_return = f"{function_return} {ret_mod}"

    # func_mod = function_retn.get("qual")
    # if func_mod is not None:
    #     func_mod = get_entry_name(func_mod)
    #     if func_mod == "c":
    #         function_return = f"{function_return} const"

    return function_return


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


def is_method(func_decl: Entry) -> bool:
    if func_decl is None:
        raise RuntimeError("case never occurred")
    if func_decl.get_type() != "function_decl":
        raise RuntimeError("case never occurred")
    scope = func_decl.get("scpe")
    if scope is None:
        raise RuntimeError("case never occurred")
    if scope.get_type() != "record_type":
        return False
    return True


# returns True if function is regular method, otherwise is a static method
def is_method_of_instance(func_decl: Entry) -> bool:
    if func_decl is None:
        return False
    args_list = func_decl.get_sub_entries("args")
    if not args_list:
        return False
    _first_prop, first_arg = args_list[0]
    first_name = get_entry_name(first_arg)
    return first_name == "this"


## find virtual methods table
def find_class_vtable_var_decl(content: LangContent, record_entry: Entry):
    ## example name of vtable: _ZTVN4item8ExampleBE

    class_full_name = get_entry_repr(record_entry)
    class_name = get_entry_name(record_entry)

    for entry in content.content_objs.values():
        if entry.get_type() != "var_decl":
            continue
        entry_name = get_entry_name(entry)
        if not entry_name.startswith("_ZTV"):
            continue
        if not class_name in entry_name:
            continue
        scpe_entry = entry.get("scpe")
        if scpe_entry is None:
            continue
        scpe_name = get_entry_repr(scpe_entry)
        if scpe_name != class_full_name:
            continue
        return entry
    return None
