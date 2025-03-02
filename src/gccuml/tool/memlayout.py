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

from gccuml.langcontent import (
    LangContent,
    Entry,
    get_entry_name,
    is_namespace_internal,
    get_record_namespace_list,
)
from gccuml.diagram.graphviz.memlayoutdiagram import MemoryLayoutDiagramGenerator, StructData, StructField, FieldType
from gccuml.langanalyze import StructAnalyzer


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
        self.analyzer = StructAnalyzer(content, include_internals)

    def generate_data(self) -> Dict[str, StructData]:
        ret_dict = {}
        dcls_list = self.content.get_entries("dcls")
        for dcls_entry in dcls_list:
            info_list = self.get_class_info(dcls_entry)
            if info_list:
                for info in info_list:
                    ret_dict[info.name] = info
        return ret_dict

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

        entry_name: str = self.analyzer.get_record_full_name(record_entry)
        if entry_name is None:
            return None

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
            field_type: str = self.analyzer.get_record_full_name(field_type_entry)

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
                field = StructField("[padding]", None, recent_end, empty_space, None, FieldType.EMPTY)
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
            field = StructField("[padding]", None, recent_end, empty_space, None, FieldType.EMPTY)
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
