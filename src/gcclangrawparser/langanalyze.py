#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging

from gcclangrawparser.langcontent import Entry, get_entry_name, is_namespace_internal


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


## ====================================================


def get_record_namespace_list(record_decl: Entry):
    if record_decl is None:
        return []
    field_type = record_decl.get("name")
    ret_list = get_type_namespace_list(field_type)
    return ret_list


def get_type_namespace_list(type_decl: Entry):
    if type_decl is None:
        return []

    ret_list = []
    item = type_decl
    while item:
        if item.get_type() == "translation_unit_decl":
            ret_list.append("")
            break
        item_name_entry = item.get("name")
        item_name = get_entry_name(item_name_entry)
        ret_list.append(item_name)
        item = item.get("scpe")

    ret_list.reverse()
    return ret_list
