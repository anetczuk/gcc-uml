#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict

from gccuml.langcontent import (
    Entry,
    get_entry_name,
    is_namespace_internal,
    get_record_namespace_list,
    get_decl_namespace_list,
    LangContent,
    get_number_entry_value,
)
from gccuml.langentrylist import ENTRY_DEF_LIST


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


class RecordInfo:

    def __init__(self):
        self.namespace_list = []
        self.template_params = []

    def get_full_name(self) -> str:
        entry_name: str = "::".join(self.namespace_list)
        if self.template_params is not None:
            template_params_str = ", ".join(self.template_params)
            entry_name = f"{entry_name}<{template_params_str}>"
        return entry_name


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

    def get_record_info(self, record_decl: Entry) -> RecordInfo:
        entry_namespace_list = get_record_namespace_list(record_decl)
        if entry_namespace_list is None:
            return None
        if not self.include_internals:
            if is_namespace_internal(entry_namespace_list):
                return None
        record_info = RecordInfo()
        record_info.namespace_list = entry_namespace_list

        template_instances_dict = self.get_template_defs()
        record_entry_id = record_decl.get_id()
        template_params = template_instances_dict.get(record_entry_id)
        record_info.template_params = template_params
        return record_info

    def get_record_full_name(self, record_decl: Entry) -> str:
        record_info = self.get_record_info(record_decl)
        if record_info is None:
            return record_info
        return record_info.get_full_name()


def get_function_full_name(function_decl: Entry):
    if function_decl is None:
        return None
    if function_decl.get_type() != "function_decl":
        raise RuntimeError("case never occurred")

    scope = function_decl.get("scpe")
    if scope is None:
        ## compiler generated function
        name_prefix = get_decl_namespace_list(function_decl)
        return "::".join(name_prefix)

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

    ## we want to display all constructors, but following code (commented) prevents it
    # method_note_list = function_decl.get_list("note")
    # if "constructor" in method_note_list:
    #     method_name = get_entry_name(scope)
    # elif "destructor" in method_note_list:
    #     class_name = get_entry_name(scope)
    #     method_name = f"~{class_name}"

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


def get_entry_repr(entry: Entry) -> str:
    if not isinstance(entry, Entry):
        return entry

    type_name = get_type_entry_name(entry)
    if type_name is not None:
        return type_name

    num_value = get_number_entry_value(entry, fail_exception=False)
    if num_value is not None:
        return num_value

    if entry.get_type() == "field_decl":
        ## in case of base classes field_decls does not have any name
        field_name = get_entry_name(entry, None)
        if field_name:
            return field_name
        field_type = entry.get("type")
        return get_entry_repr(field_type)

    return get_entry_name(entry)


def get_type_entry_name(type_entry: Entry):
    name, const_mod = get_type_name_mod(type_entry)
    if name is None:
        return None
    if const_mod is None:
        return name
    return f"{name} {const_mod}"


def get_type_name_mod(type_entry: Entry):
    parm_mod = None
    arg_qual = type_entry.get("qual")
    if arg_qual == "c":
        parm_mod = "const"

    entry_type = type_entry.get_type()

    if entry_type == "pointer_type":
        ptd = type_entry.get("ptd")
        pointer_entry_name = get_entry_name(type_entry, default_ret=None)
        pointer_name = pointer_entry_name
        if pointer_name is None:
            pointer_name = get_full_name(ptd)
        if pointer_name is None:
            return (None, parm_mod)
        if pointer_entry_name is None:
            if pointer_name.endswith("*"):
                pointer_name += "*"
            else:
                pointer_name += " *"
        return (pointer_name, parm_mod)

    if entry_type == "reference_type":
        refd = type_entry.get("refd")
        refd_name = get_full_name(refd)
        refd_name += " &"
        return (refd_name, parm_mod)

    if entry_type == "array_type":
        elms = type_entry.get("elts")
        elms_name = get_type_entry_name(elms)
        return (f"{elms_name}[]", parm_mod)

    name_list = get_decl_namespace_list(type_entry)
    if name_list:
        param_name = "::".join(name_list)
        return (param_name, parm_mod)

    param_name = get_entry_name(type_entry, default_ret=None)
    return (param_name, parm_mod)


def get_full_name(entry: Entry) -> str:
    entry_type = entry.get_type()
    if entry_type == "function_type":
        ret_type = get_function_ret(entry)
        params_list = get_func_type_parameters(entry)
        params_str = ", ".join(params_list)
        return f"{ret_type} ({params_str})"
    return get_type_entry_name(entry)


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
        arg_type_full = get_type_entry_name(arg_type_entry)
        args_list.append([arg_name, arg_type_full])
    return args_list


def get_function_ret(function_type: Entry):
    function_retn = function_type.get("retn")
    if function_retn is None:
        return None
    function_return = get_type_entry_name(function_retn)

    # func_mod = function_retn.get("qual")
    # if func_mod is not None:
    #     func_mod = get_entry_name(func_mod)
    #     if func_mod == "c":
    #         function_return = f"{function_return} const"

    return function_return


def get_func_type_parameters(function_type: Entry):
    return get_template_parameters(function_type)


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
        if not sub_list:
            # example case: 'void func1(void);'
            valu_name = get_entry_name(valu)
            ret_list.append(valu_name)
            continue

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


## find virtual methods table Entry
def find_class_vtable_var_decl(content: LangContent, record_entry: Entry) -> Entry:
    ## example name of vtable: _ZTVN4item8ExampleBE

    class_full_name = get_entry_repr(record_entry)
    class_name = get_entry_name(record_entry)

    for entry in content.content_objs.values():
        if entry.get_type() != "var_decl":
            continue
        entry_name = get_entry_name(entry)
        if not entry_name.startswith("_ZTV"):
            continue
        if class_name not in entry_name:
            continue
        scpe_entry = entry.get("scpe")
        if scpe_entry is None:
            continue
        scpe_name = get_entry_repr(scpe_entry)
        if scpe_name != class_full_name:
            continue
        return entry
    return None


## find virtual methods table Dict
def get_vtable_entries(vtable_var_decl: Entry) -> Dict[int, Entry]:
    tab_dict = {}
    var_init = vtable_var_decl.get("init")
    items_num = int(var_init.get("lngt"))
    data_list = var_init.get_ordered_tuples(["idx", "val"])
    if len(data_list) != items_num:
        raise RuntimeError("invalid number of values in entry: {statement_entry}")
    for index, data_item in enumerate(data_list):
        data_idx = data_item[0]
        data_val = data_item[1]
        idx_expr = index
        if data_idx:
            idx_expr = get_number_entry_value(data_idx)
            idx_expr = int(idx_expr)
        subval_entry = data_val.get("op 0")
        if subval_entry.get_type() == "addr_expr":
            subval_entry = subval_entry.get("op 0")
        tab_dict[idx_expr] = subval_entry
    return tab_dict


## ==================================================


_TYPE_TO_CODE_CLASS_DICT: Dict[str, str] = None


def get_entry_type_code_class(entry_type: str) -> str:
    # pylint: disable=W0603
    global _TYPE_TO_CODE_CLASS_DICT
    if _TYPE_TO_CODE_CLASS_DICT is None:
        ## build dict
        _TYPE_TO_CODE_CLASS_DICT = {}
        for item in ENTRY_DEF_LIST:
            item_name = item[1]
            code_class = item[2]
            _TYPE_TO_CODE_CLASS_DICT[item_name] = code_class
    return _TYPE_TO_CODE_CLASS_DICT.get(entry_type)


def is_entry_code_class(entry: Entry, code_class):
    type_name = entry.get_type()
    entry_code_class = get_entry_type_code_class(type_name)
    return entry_code_class == code_class
