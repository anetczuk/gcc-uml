#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
import re
from typing import Dict, Any, Tuple, List

from gccuml.langcontent import LangContent


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


def parse_raw(input_path: str, reducepaths: str = None) -> LangContent:
    if not os.path.isfile(input_path):
        return None
    _LOGGER.debug("reading input file")
    content_lines = read_raw_file(input_path)
    content_dict = convert_bytes_to_dict(content_lines, reducepaths)
    _LOGGER.debug("parsing raw content")
    return LangContent(content_dict)


# =========================================


def convert_lines_to_dict(content_lines, reducepaths=None) -> Dict[str, Any]:
    content_bytes = [item.encode(encoding="utf-8") for item in content_lines]
    return convert_bytes_to_dict(content_bytes, reducepaths=reducepaths)


def convert_bytes_to_dict(content_bytes, reducepaths=None) -> Dict[str, Any]:
    reduce_len = 0
    if reducepaths:
        reduce_len = len(reducepaths)
    content_dict = {}
    converter = ProprertiesConverter()
    for line in content_bytes:
        # there can be item with no parameters
        ## regex: <ID><whitespaces><type><properties>
        found = re.search(rb"^(\S+)\s+(\S+)(\s+.*)?$", line, re.MULTILINE | re.DOTALL)
        if not found:
            raise RuntimeError(f"unable to parse line: '{line}'")
        # print(f"{line} -> >{found.group(1)}< >{found.group(2)}< >{found.group(3)}<")
        line_id = found.group(1)
        line_type = found.group(2)
        props_raw_data = found.group(3)

        line_id = line_id.decode("utf-8")
        line_type = line_type.decode("utf-8")
        props_list = converter.convert_type_bytes(line_type, props_raw_data)

        if reducepaths:
            for index, prop_data in enumerate(props_list.copy()):
                prop_val = prop_data[1]
                if prop_val.startswith(reducepaths):
                    prop_key = prop_data[0]
                    reduced_val = prop_val[reduce_len:]
                    props_list[index] = (prop_key, reduced_val)
        content_dict[line_id] = (line_id, line_type, props_list)
    return content_dict


class ProprertiesConverter:

    def __init__(self, properties_str=""):
        self.raw_properties = properties_str.encode(encoding="utf-8")

    def convert_type_bytes(self, type_name, properties_bytes) -> List[Tuple[str, str]]:
        if type_name == "string_cst":
            ## "strg" field of "string_cst" in special case can be any value including field name itself
            ## so it needs to be handled in special way
            return self.convert_bytes_string_cst(properties_bytes)

        if type_name == "field_decl":
            ## compatibility with old gcc versions where "bitfield" string is appended to
            ## one of field values
            props_list = self.convert_bytes(properties_bytes)
            for index, item in enumerate(props_list.copy()):
                field, value = item
                if "bitfield" in value:
                    bitfield_pos = value.index("bitfield")
                    value = value[:bitfield_pos]
                    value = value.rstrip()
                    props_list[index] = (field, value)
                    props_list.append(("bitfield", "1"))
            return props_list

        ## general solution
        return self.convert_bytes(properties_bytes)

    def convert(self, properties_str: str) -> List[Tuple[str, str]]:
        properties_bytes = properties_str.encode(encoding="utf-8")
        return self.convert_bytes(properties_bytes)

    def convert_bytes(self, properties_bytes) -> List[Tuple[str, str]]:
        self.raw_properties = properties_bytes

        raw_list = []
        while self.raw_properties:
            next_key = self.consume_key()
            next_val = self.consume_value()
            next_key = next_key.decode("utf-8")
            next_val = next_val.decode("utf-8")
            raw_list.append((next_key, next_val))
        return raw_list

    def convert_string_cst(self, properties_str):
        properties_bytes = properties_str.encode(encoding="utf-8")
        return self.convert_bytes_string_cst(properties_bytes)

    def convert_bytes_string_cst(self, properties_bytes):
        ## we assume that "lngt" field is the last one
        ## and "strg" goes before "lngt"
        self.raw_properties = properties_bytes

        raw_list = []

        ## reading type field
        type_key = self.consume_key()
        type_val = self.consume_value()
        type_key = type_key.decode("utf-8")
        type_val = type_val.decode("utf-8")
        raw_list.append((type_key, type_val))

        ## reading length field
        last_val = self.consume_word_right()
        last_key = self.consume_key_right()
        last_val = last_val.decode("utf-8")
        last_key = last_key.decode("utf-8")
        if last_key != "lngt":
            raise RuntimeError("invalid data")
        length_value = int(last_val)

        ## reading string field
        strg_key = self.consume_key(strip_props=False)
        strg_key = strg_key.decode("utf-8")
        strg_value = self.raw_properties
        try:
            strg_value = strg_value.decode("utf-8")
            strg_len = len(strg_value)
            expected_len = min(strg_len, length_value - 1)
            strg_value = strg_value[0:expected_len]

            ## escape twice to prevent unescaping in plantuml/dot to svg conversion
            strg_value = strg_value.encode("unicode-escape")  ## escapes newlines (prevents \n)
            strg_value = strg_value.decode("utf-8")
            strg_value = strg_value.encode("unicode-escape")  ## escapes newlines (prevents \n)
            strg_value = strg_value.decode("utf-8")

        except UnicodeDecodeError:
            ## there is rare situation where "strg" field contains UTF-8 invalid characters
            ## it happens, e.g. during C-array initialization
            strg_value = strg_value.hex()
            strg_len = len(strg_value)
            expected_len = min(strg_len, length_value * 2)
            strg_value = strg_value[0:expected_len]
            strg_value = strg_value.upper()
            strg_value = "0x" + strg_value
        self.raw_properties = b""
        raw_list.append((strg_key, strg_value))
        raw_list.append((last_key, last_val))
        return raw_list

    def consume_key(self, strip_props=True):
        next_colon_pos = self.raw_properties.index(b": ")
        key = self.raw_properties[:next_colon_pos]
        self.raw_properties = self.raw_properties[next_colon_pos + 1 :]  # remove colon
        if strip_props:
            self.raw_properties = self.raw_properties.lstrip()
        else:
            ## remove first leading space
            if len(self.raw_properties) > 0:
                self.raw_properties = self.raw_properties[1:]
        return key.strip()

    def consume_value(self):
        if self.raw_properties.startswith(b"@"):
            # identifier case - easy path
            try:
                next_space_pos = self.raw_properties.index(b" ")
            except ValueError:
                # only value left
                value = self.raw_properties
                value = value.strip()
                self.raw_properties = b""
                return value
            value = self.raw_properties[:next_space_pos]
            value = value.strip()
            self.raw_properties = self.raw_properties[next_space_pos + 1 :]
            self.raw_properties = self.raw_properties.lstrip()
            return value

        try:
            next_key_colon_pos = self.raw_properties.index(b": ")
            with_next_key_str = self.raw_properties[:next_key_colon_pos].rstrip()
            if b" " not in with_next_key_str:
                # special case: value is '::" (global namespace symbol)
                next_key_colon_pos = self.raw_properties.index(b": ", next_key_colon_pos + 1)
                with_next_key_str = self.raw_properties[:next_key_colon_pos].rstrip()
        except ValueError:
            # only value left
            value = self.raw_properties
            value = value.strip()
            self.raw_properties = b""
            return value

        last_space_pos = with_next_key_str.rindex(b" ")
        value = self.raw_properties[: last_space_pos + 1]
        value = value.strip()
        self.raw_properties = self.raw_properties[last_space_pos + 1 :]
        return value

    def consume_key_right(self):
        self.raw_properties = self.raw_properties.rstrip()
        fied_key = self.consume_word_right()
        if len(fied_key) > 1:
            return fied_key[:-1]  ## drop semicolon

        # only colon - there are spaces in key name
        fied_key = self.consume_word_right()
        return fied_key

    def consume_word_right(self):
        self.raw_properties = self.raw_properties.rstrip()
        try:
            last_space_pos = self.raw_properties.rindex(b" ")
            value = self.raw_properties[last_space_pos + 1 :]
            self.raw_properties = self.raw_properties[: last_space_pos + 1]
            return value
        except ValueError:
            # only value left
            value = self.raw_properties
            value = value.strip()
            self.raw_properties = b""
            return value


def read_raw_file(input_path):
    try:
        # with open(input_path, "r", encoding="utf-8", errors='ignore') as content_file:
        with open(input_path, "rb") as content_file:
            # with open(input_path, "r", encoding="utf-8") as content_file:
            content_list = []
            curr_line = b""
            for line in content_file:
                if line.startswith(b"@"):
                    ## start of new line
                    content_list.append(curr_line)
                    curr_line = line.rstrip()
                    continue
                ## join lines
                curr_line += b"\n " + line.rstrip()

            content_list.append(curr_line)
            if content_list:
                content_list = content_list[1:]
            return content_list
    except BaseException:
        _LOGGER.error("unable to read file: %s", input_path)
        raise
