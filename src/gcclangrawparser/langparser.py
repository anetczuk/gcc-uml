#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import re
from typing import Dict

from gcclangrawparser.langcontent import LangContent


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_raw(input_path, reducepaths) -> LangContent:
    if not os.path.isfile(input_path):
        return None
    content_lines = read_raw_file(input_path)
    return parse_raw_content(content_lines, reducepaths)


def parse_raw_content(content_lines, reducepaths) -> LangContent:
    content_dict = convert_lines_to_dict(content_lines, reducepaths)
    return LangContent(content_dict)


# =========================================


def convert_lines_to_dict(content_lines, reducepaths):
    reduce_len = len(reducepaths)
    content_dict = {}
    converter = ProprertiesConverter()
    for line in content_lines:
        # there can be item with no parameters
        found = re.search(r"^(\S+)\s+(\S+)(\s+.*)?$", line)
        if not found:
            raise RuntimeError(f"unable to parse line: '{line}'")
        # print(f"{line} -> >{found.group(1)}< >{found.group(2)}< >{found.group(3)}<")
        line_id = found.group(1)
        line_type = found.group(2)
        line_props = converter.convert(found.group(3))
        if reducepaths:
            for prop_key, prop_val in list(line_props.items()):
                if prop_val.startswith(reducepaths):
                    line_props[prop_key] = prop_val[reduce_len:]
        content_dict[line_id] = (line_id, line_type, line_props)
    return content_dict


class ProprertiesConverter:

    def __init__(self):
        self.raw_properties = ""

    def convert(self, properties_str) -> Dict[str, str]:
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
