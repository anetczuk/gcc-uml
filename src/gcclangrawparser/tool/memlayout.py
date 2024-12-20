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
from gcclangrawparser.diagram.memlayoutdiagram import MemoryLayoutDiagramGenerator, StructData, StructField, FieldType


_LOGGER = logging.getLogger(__name__)


def generate_memory_layout_graph(content: LangContent, out_path, include_internals=False, graphnote=None):
    _LOGGER.info("generating memory layout graph to %s", out_path)
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_entries()

    mem_data = MemoryLayoutData(content, include_internals)
    mem_info = mem_data.generate_data()

    diagram_gen = MemoryLayoutDiagramGenerator(mem_info)
    diagram_gen.generate(out_path, graphnote=graphnote)

    _LOGGER.info("generating completed")


class MemoryLayoutData:

    def __init__(self, content, include_internals=False):
        self.content = content
        self.include_internals = include_internals
        self.template_instances_dict = {}

    def generate_data(self) -> Dict[str, StructData]:
        ret_dict = {}
        dcls_list = self._get_entries("dcls")
        self._process_decls(dcls_list)
        for dcls_entry in dcls_list:
            info_list = self.get_class_info(dcls_entry)
            if info_list:
                for info in info_list:
                    ret_dict[info.name] = info
        return ret_dict

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

    def get_class_info(self, dcls_entry: Entry) -> List[StructData]:
        class_data_list = None

        if dcls_entry.get_type() == "type_decl":
            class_data_list = self._get_class_type_decl(dcls_entry)

        elif dcls_entry.get_type() == "template_decl":
            class_data_list = self._get_class_template_decl(dcls_entry)

        if class_data_list:
            class_names = [item.name for item in class_data_list]
            _LOGGER.info("found items %s for entry %s", class_names, dcls_entry.get_id())

        return class_data_list

    def _get_class_type_decl(self, type_decl: Entry) -> List[StructData]:
        record_entry = type_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", type_decl.get_id())
            return None
        if record_entry.get_type() != "record_type":
            return None

        record_size_entry = record_entry.get("size")
        if record_size_entry is None:
            return None
        record_size = record_size_entry.get("int")
        if record_size is None:
            return None
        record_size = int(record_size)

        entry_namespace_list = get_record_namespace_list(record_entry)
        if entry_namespace_list is None:
            return None
        if not self.include_internals:
            if is_namespace_internal(entry_namespace_list):
                return None
        entry_name: str = "::".join(entry_namespace_list)

        record_entry_id = record_entry.get_id()
        template_params = self.template_instances_dict.get(record_entry_id)
        if template_params is not None:
            template_params_str = ", ".join(template_params)
            entry_name = f"{entry_name}<{template_params_str}>"

        class_data = StructData(entry_name, record_size)

        field_list = self.get_fields_list(record_entry)
        class_data.fields = field_list

        return [class_data]

    def _get_class_template_decl(self, template_decl: Entry) -> List[StructData]:
        record_entry = template_decl.get("type")
        if record_entry is None:
            _LOGGER.info("entry %s has no record_type", template_decl.get_id())
            return None
        if record_entry.get_type() != "record_type":
            return None

        record_size_entry = record_entry.get("size")
        if record_size_entry is None:
            return None
        record_size = record_size_entry.get("int")
        if record_size is None:
            return None
        record_size = int(record_size)

        type_name = get_entry_name(template_decl)
        templ_params = get_template_parameters(template_decl)
        params_str = ", ".join(templ_params)
        type_name = f"""{type_name}<{params_str}>"""

        entry_namespace_list = get_record_namespace_list(record_entry)
        if entry_namespace_list is None:
            return None
        if not self.include_internals:
            if is_namespace_internal(entry_namespace_list):
                return None
        entry_name: str = "::".join(entry_namespace_list)

        class_data = StructData(entry_name, record_size)

        field_list = self.get_fields_list(record_entry)
        class_data.fields = field_list

        ret_list = [class_data]

        ## read instances
        instantiations_entry = template_decl.get("inst")
        insts_size = int(instantiations_entry.get("lngt"))
        for inst_index in range(0, insts_size):
            inst_index_str = str(inst_index)
            inst_entry = instantiations_entry.get(inst_index_str)
            valu_record_entry = inst_entry.get("valu")
            valu_type_entry = valu_record_entry.get("name")
            instance_info = self._get_class_type_decl(valu_type_entry)
            if instance_info:
                ret_list.extend(instance_info)

        return ret_list

    def get_fields_list(self, record_entry: Entry):
        ret_list = []
        flds_entries = record_entry.get_sub_entries("flds")

        recent_end = 0
        for _prop, field_item in flds_entries:
            item_type = field_item.get_type()
            if item_type != "field_decl":
                # field is defined as field_decl
                continue

            field_type_entry = field_item.get("type")

            type_namespace = get_field_namespace_list(field_item)
            field_type = "::".join(type_namespace)

            field_type_id = field_type_entry.get_id()
            field_template_params = self.template_instances_dict.get(field_type_id)
            if field_template_params is not None:
                template_params_str = ", ".join(field_template_params)
                field_type = f"{field_type}<{template_params_str}>"

            is_vtable = False
            is_baseclass = False
            field_name_entry = field_item.get("name")
            field_name = get_entry_name(field_name_entry)
            if field_name is not None:
                if field_name.startswith("_vptr."):
                    # ignore vtable
                    # field_name = "vtbl **"
                    field_type = None
                    is_vtable = True
            else:
                is_baseclass = True

            field_pos = 0
            field_bpos_entry = field_item.get("bpos")  # template field does no have this entry
            if field_bpos_entry is not None:
                field_pos = field_bpos_entry.get("int")
                if field_pos is not None:
                    field_pos = int(field_pos)

            empty_space = field_pos - recent_end
            if empty_space > 0:
                field = StructField("[empty]", None, recent_end, empty_space, None, FieldType.EMPTY)
                ret_list.append(field)

            field_size = 0
            field_size_entry = field_item.get("size")
            if field_size_entry is not None:
                field_size = field_size_entry.get("int")
                if field_size is not None:
                    field_size = int(field_size)

            recent_end = field_pos + field_size

            ftype = FieldType.REGULAR
            if is_baseclass:
                ftype = FieldType.BASECLASS
            elif is_vtable:
                ftype = FieldType.VTABLE

            field = StructField(field_name, field_type, field_pos, field_size, [field_type, None], ftype)
            ret_list.append(field)

        record_size_entry = record_entry.get("size")
        if record_size_entry is None:
            return None
        record_size = record_size_entry.get("int")
        if record_size is None:
            return None
        record_size = int(record_size)

        empty_space = record_size - recent_end
        if empty_space > 0:
            field = StructField("[empty]", None, recent_end, empty_space, None, FieldType.EMPTY)
            ret_list.append(field)

        # record_namespace_list = get_record_namespace_list(record_entry)
        # if record_namespace_list is None:
        #     return None
        # record_name: str = "::".join(record_namespace_list)
        #
        # vfld_entry_list = record_entry.get_sub_entries("vfld")
        # for vfld_item in vfld_entry_list:
        #     vfld_entry = vfld_item[1]
        #     vfield_name = get_entry_name(vfld_entry)
        #     scpe_entry = vfld_entry.get_sub_entries("scpe")
        #     scpe_entry = scpe_entry[0][1]
        #     type_namespace_listt = get_record_namespace_list(scpe_entry)
        #     type_name: str = "::".join(type_namespace_listt)
        #
        #     if type_name != record_name:
        #         field = StructField(vfield_name, None, "vtbl*", None, (type_name, vfield_name), FieldType.VTABLE)
        #         ret_list.append(field)

        return ret_list

    def _get_identifier_nodes(self):
        ret_list = []
        for entry in self.content.content_objs.values():
            if entry.get_type() != "identifier_node":
                continue
            if not self.include_internals:
                if is_entry_language_internal(entry):
                    continue
            ret_list.append(entry)
        return ret_list

    def _get_entries(self, prop):
        ret_list = []
        # entry: Entry
        for entry in self.content.content_objs.values():
            if not self.include_internals:
                if is_entry_language_internal(entry):
                    continue
            sub_entries = entry.get_sub_entries(prop)
            for item in sub_entries:
                ret_list.append(item[1])
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


def get_field_namespace_list(field_decl: Entry):
    if field_decl is None:
        return []
    field_record = field_decl.get("type")
    return get_record_namespace_list(field_record)


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
