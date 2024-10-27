#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import re
import pprint

from munch import Munch


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_raw(input_path):
    if not os.path.isfile(input_path):
        return None
    content_lines = read_raw_file(input_path)
    return parse_raw_content(content_lines)


def parse_raw_content(content_lines):
    content_dict = convert_lines_to_dict(content_lines)
    return LangContent(content_dict)


# =========================================


class Entry(Munch):
    """Base project representing entry in lang raw file.

    Access to object data is possible through dict interface (array operator) or by dot operator.
    Every object has two properties: _id and _type. They are available through getters.
    """

    def __init__(self, props_dict):
        self._id = None
        self._type = None
        super().__init__(props_dict)

    def get_id(self):
        return self._id

    def get_type(self):
        return self._type

    # prevents recursive error
    def __str__(self) -> str:
        obj_dict = dict(self)
        return obj_dict.__str__()

    # prevents recursive error
    def __repr__(self) -> str:
        return f"<Entry {self._id}>"


class LangContent:

    def __init__(self, content_dict):
        self.content_lines = content_dict
        self.types_fields = self._prepare_types_fields()
        self.content_objs = self._objectify()

    def _prepare_types_fields(self):
        ret_types_dict = {}
        for _key, entry in self.content_lines.items():
            entry_type = entry[1]
            entry_data = entry[2]

            type_props = ret_types_dict.get(entry_type, {})
            for prop_key, prop_val in entry_data.items():
                if entry_type == "identifier_node":
                    if prop_key == "strg":
                        type_props[prop_key] = ["<string>"]
                        continue
                    if prop_key == "lngt":
                        type_props[prop_key] = ["<unsigned number>"]
                        continue
                if entry_type == "integer_cst":
                    if prop_key == "int":
                        type_props[prop_key] = ["<number>"]
                        continue

                prop_values = type_props.get(prop_key, [])
                prop_values = set(prop_values)
                if prop_val.startswith("@"):
                    # identifier
                    prop_values.add("<entry-id>")
                else:
                    prop_values.add(prop_val)
                type_props[prop_key] = sorted(prop_values)

            type_props = dict(sorted(type_props.items()))
            ret_types_dict[entry_type] = type_props

        ret_types_dict = dict(sorted(ret_types_dict.items()))
        return ret_types_dict

    def _objectify(self):
        ret_objs_dict = {}
        for key, entry in self.content_lines.items():
            entry_type = entry[1]
            entry_data = entry[2]
            obj_dict = {"_id": key, "_type": entry_type}
            obj_dict.update(entry_data)
            ret_objs_dict[key] = Entry(obj_dict)
        for _key, object_item in ret_objs_dict.items():
            for field, value in object_item.items():
                if field == "_id":
                    continue
                if value.startswith("@"):
                    object_item[field] = ret_objs_dict[value]
        return ret_objs_dict

    def print_types_fields(self):
        pprint.pprint(self.types_fields, indent=4)

    def print_namespaces(self):
        find_type = "namespace_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                scope_obj = entry["scpe"]
                scope_name = get_entry_name(scope_obj)
                source_point = entry["srcp"]
                lang = entry.get("lang", "<--no entry-->")
                type_name = entry.get("type", "<--no entry-->")
                type_name = get_entry_name(type_name)
                print(f"{entry.get_id()}: {entry.get_type()}")
                print(f"    name: {entry_name}")
                print(f"    scpe: {scope_name}")
                print(f"    lang: {lang}")
                print(f"    srcp: {source_point}")
                print(f"    type: {type_name}")
                ## chain - not important?
                ## dcls - not important? can be assumed from 'scpe' of other entries pointing to the namespace

    def print_translation_units(self):
        find_type = "translation_unit_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                print(f"{entry.get_id()}: {entry_name}")

    def print_functions(self):
        find_type = "function_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                mngl_name = entry.get("mngl", "<--no entry-->")
                mngl_name = get_entry_name(mngl_name)
                # type_name = entry.get("type", "<--no entry-->")
                # type_name = get_entry_name(type_name)
                print(f"{entry.get_id()} -> {entry.get_type()}")
                print(f"    name: {entry_name}")
                print(f"    mngl: {mngl_name}")
                # print(f"    type: {type_name}")

    # def get_name(self, entry_id, optional=False, default=None):
    #     identifier_entry = self.content_lines[entry_id]
    #     identifier_props = identifier_entry[2]
    #     try:
    #         if optional:
    #             return identifier_props.get("strg", default)
    #         return identifier_props["strg"]
    #     except KeyError:
    #         print(f"invalid props - key: {entry_id} props: {identifier_props}")
    #         raise
    #
    # def get_scope_name(self, entry_id, optional=False, default=None):
    #     identifier_entry = self.content_lines[entry_id]
    #     identifier_props = identifier_entry[2]
    #     try:
    #         if optional:
    #             return identifier_props.get("name", default)
    #         return identifier_props["name"]
    #     except KeyError:
    #         print(f"invalid props - key: {entry_id} props: {identifier_props}")
    #         raise


# =========================================


def get_entry_name(entry):
    if not isinstance(entry, Entry):
        return entry

    entry_type = entry.get_type()

    if entry_type == "namespace_decl":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    if entry_type == "identifier_node":
        try:
            entry_value = entry.get("strg", "<--no entry-->")
            return get_entry_name(entry_value)
        except KeyError:
            print(f"invalid props - {entry}")
            raise

    if entry_type == "translation_unit_decl":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    if entry_type == "function_decl":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    if entry_type == "void_type":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    if entry_type == "type_decl":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    if entry_type == "function_type":
        entry_value = entry["name"]
        return get_entry_name(entry_value)

    raise RuntimeError(f"unhandled entry type: {entry.get_id()} {entry_type}")


def convert_lines_to_dict(content_lines):
    content_dict = {}
    converter = ProprertiesConverter()
    for line in content_lines:
        found = re.search(r"^(\S+)\s+(\S+)\s+(.*)$", line)
        if not found:
            raise RuntimeError(f"unable to parse line: '{line}'")
        # print(f"{line} -> >{found.group(1)}< >{found.group(2)}< >{found.group(3)}<")
        line_id = found.group(1)
        line_type = found.group(2)
        line_props = converter.convert(found.group(3))
        content_dict[line_id] = (line_id, line_type, line_props)
    return content_dict


class ProprertiesConverter:

    def __init__(self):
        self.raw_properties = ""

    def convert(self, properties_str):
        self.raw_properties = properties_str
        ret_dict = {}
        while self.raw_properties:
            next_key = self.consume_key()
            next_val = self.consume_value()
            # print(f"gggg: >{next_key}< >{next_val}<")
            ret_dict[next_key] = next_val
        return ret_dict

    def consume_key(self):
        next_colon_pos = self.raw_properties.index(": ")
        key = self.raw_properties[:next_colon_pos]
        self.raw_properties = self.raw_properties[next_colon_pos + 1 :]  # remove colon
        self.raw_properties = self.raw_properties.lstrip()
        return key.strip()

    def consume_value(self):
        if self.raw_properties.startswith("@"):
            # identifier case - easy path
            try:
                next_space_pos = self.raw_properties.index(" ")
            except ValueError:
                # only value left
                value = self.raw_properties
                value = value.strip()
                self.raw_properties = ""
                return value
            value = self.raw_properties[:next_space_pos]
            value = value.strip()
            self.raw_properties = self.raw_properties[next_space_pos + 1 :]
            self.raw_properties = self.raw_properties.lstrip()
            return value

        try:
            next_key_colon_pos = self.raw_properties.index(": ")
            with_next_key_str = self.raw_properties[:next_key_colon_pos].rstrip()
            if " " not in with_next_key_str:
                # special case: value is '::" (global namespace symbol)
                next_key_colon_pos = self.raw_properties.index(": ", next_key_colon_pos + 1)
                with_next_key_str = self.raw_properties[:next_key_colon_pos].rstrip()
        except ValueError:
            # only value left
            value = self.raw_properties
            value = value.strip()
            self.raw_properties = ""
            return value

        last_space_pos = with_next_key_str.rindex(" ")
        value = self.raw_properties[: last_space_pos + 1]
        value = value.strip()
        self.raw_properties = self.raw_properties[last_space_pos + 1 :]
        return value


def read_raw_file(input_path):
    with open(input_path, "r", encoding="utf-8") as content_file:
        content_list = []
        curr_line = ""
        for line in content_file:
            if line.startswith("@"):
                ## start of new line
                content_list.append(curr_line)
                curr_line = line.rstrip()
                continue
            curr_line += " " + line.rstrip()
        content_list.append(curr_line)
        if content_list:
            content_list = content_list[1:]
        return content_list
