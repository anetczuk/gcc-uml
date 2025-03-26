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
    LangContent,
    get_number_entry_value,
    get_entry_repr, get_full_name,
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
                        purp_type_name = get_full_name(purp_type_entry)
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
