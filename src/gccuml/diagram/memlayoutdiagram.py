# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from enum import Enum, auto
from typing import NamedTuple
from typing import List, Dict
import html

from showgraph.io import write_file, read_list


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


BG_COLORS_PATH = os.path.join(SCRIPT_DIR, "plantuml_bg_colors.txt")
BG_COLORS_LIST = read_list(BG_COLORS_PATH)


## ===========================================================


class FieldType(Enum):
    REGULAR = auto()
    BASECLASS = auto()
    VTABLE = auto()
    EMPTY = auto()


StructField = NamedTuple(
    "StructField",
    [("name", str), ("type", str), ("pos", int), ("size", int), ("connect", list), ("fieldtype", FieldType)],
)


class StructData:
    """Container for struct data to be presented on graph."""

    def __init__(self, name, size):
        self.name: str = name
        self.size: int = size
        self.fields: List[StructField] = []


## ===========================================================


COLOR_BG_CLASS_HEADER = "PaleGreen"
COLOR_BG_CLASS_INHERIT = "#FEFECE"  # light yellow
COLOR_BG_CLASS_VTABLE = "#ffdada"  # light pink
COLOR_BG_TEMPLATE = "#cde6ff"  # light blue
COLOR_BG_EMPTY = "lightgray"


## Generator for Graphviz dot diagram
class MemoryLayoutDiagramGenerator:

    def __init__(self, memlayout_dict=None):
        self.memory_layout: Dict[str, StructData] = memlayout_dict
        if self.memory_layout is None:
            self.memory_layout = {}
        self.content_list = []
        self.actors_set = set()

    def generate(self, out_path, graphnote=None):
        if not self.memory_layout:
            ## empty data
            content = """\
digraph memory_layout {
}
"""
            _LOGGER.info("writing output to file %s", out_path)
            write_file(out_path, content)
            return

        self.content_list = []

        ##
        ## generate
        ##
        self.content_list.append(
            """\
digraph memory_layout {

fontname="Helvetica,Arial,sans-serif"
node [fontname="Helvetica,Arial,sans-serif"]
edge [fontname="Helvetica,Arial,sans-serif"]

graph [
    rankdir = "LR"
];
node [
    fontsize = "16"
    shape = "record"
];

ranksep = 2


# items subgraph
{
"""
        )

        self._add_nodes()

        self._add_connections()

        ##
        ## close diagram
        ##
        if graphnote:
            note_content = graphnote
            nlines = graphnote.count("\n")
            note_content = note_content.replace("\n", r"\l")

            rank_content = ""
            if nlines > 10:
                rank_content = "\n    rank=source"

            self.content_list.append(
                rf"""
# note subgraph
{{{rank_content}
    note [
        shape=box
        margin=0.2
        fontsize=16
        fontname="Ubuntu Mono"
        tooltip="[stackcollapse]"
        label="{note_content}\l"
    ]
}}
"""
            )

        self.content_list.append("""}  # end of graph\n""")
        content = "\n".join(self.content_list)

        # print(f"\ndiagram:\n{content}")

        _LOGGER.info("writing output to file %s", out_path)
        write_file(out_path, content)

    def _add_nodes(self):
        self.actors_set = set()

        for struct_data in self.memory_layout.values():
            actor_name = struct_data.name
            self.actors_set.add(actor_name)
            struct_size = struct_data.size
            actor_id = name_to_id(actor_name)
            actor_name = escape_name(actor_name)

            heading_color = COLOR_BG_CLASS_HEADER
            if struct_size < 1 and len(struct_data.fields) > 0:
                heading_color = COLOR_BG_TEMPLATE

            self.content_list.append(
                f"""\
    "{actor_id}" [
        shape=plain
        label=
        <<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
            <tr> <td colspan="3" bgcolor="{heading_color}" port='-1'> """
                f"""<b>{actor_name}</b>  ({struct_size}b)</td> </tr>"""
            )

            for field_index, field_item in enumerate(struct_data.fields):
                field_name, field_type, field_pos, field_size, _field_conn, field_fieldtype = field_item

                field_type_label = None
                if field_type:
                    field_type_label = html.escape(field_type)

                field_port = f"{field_index}"
                field_port = name_to_id(field_port)
                table_row = generate_table_row(
                    field_pos, field_size, field_name, field_type_label, field_port, field_fieldtype
                )
                self.content_list.append(
                    f"""\
            {table_row}"""
                )

            self.content_list.append(
                """\
        </table>>
    ]
"""
            )

        self.content_list.append("")

    def _add_connections(self):
        for struct_data in self.memory_layout.values():
            struct_name = struct_data.name
            if struct_name not in self.actors_set:
                continue

            template_parts = struct_name.split("<")
            if len(template_parts) > 1:
                # template instantiation detected - connect to template
                template_name = template_parts[0]
                self._add_connection(struct_name, "-1", template_name, "-1")

            for field_index, field_item in enumerate(struct_data.fields):
                field_conn = field_item[4]
                if field_conn is None:
                    continue
                field_conn_struct = field_conn[0]
                field_conn_field = field_conn[1]
                if field_conn_struct not in self.actors_set:
                    continue

                field_fieldtype = field_item[5]
                conn_style = ""
                if field_fieldtype == FieldType.VTABLE:
                    conn_style = "dashed"

                from_field_port = f"out_{field_index}"
                if field_conn_field:
                    field_index = self._find_field_index(field_conn_struct, field_conn_field)
                    target_port = "-1"
                    if field_index > -1:
                        target_port = f"in_{field_index}"
                    self._add_connection(struct_name, from_field_port, field_conn_struct, target_port, conn_style)
                else:
                    target_port = "-1"
                    self._add_connection(struct_name, from_field_port, field_conn_struct, "-1", conn_style)

        self.content_list.append(
            """
}  # end of items subgraph
"""
        )

    def _find_field_index(self, struct_type, struct_field):
        for struct_data in self.memory_layout.values():
            struct_name = struct_data.name
            if struct_type != struct_name:
                continue
            for field_index, field_item in enumerate(struct_data.fields):
                field_name = field_item[0]
                if field_name == struct_field:
                    return field_index
        return -1

    def _add_connection(self, from_item, from_port, to_item, to_port, style=None):
        from_actor_id = name_to_id(from_item)
        to_actor_id = name_to_id(to_item)
        if not style:
            style = ""
        else:
            style = f"""[style="{style}"]"""
        self.content_list.append(
            f"""\
    "{from_actor_id}":"{from_port}" -> "{to_actor_id}":"{to_port}"{style}"""
        )


def name_to_id(name):
    if name is None:
        return None
    name = name.replace("::", "-")
    name = html.escape(name)
    return name


def escape_name(name):
    return html.escape(name)


def generate_table_row(position, size, field_name=None, field_type=None, port=None, field_fieldtype=None):
    field_content = ""
    if field_name:
        field_content = f"{field_name}"
        if field_type:
            field_content = f"{field_content}: {field_type}"
    else:
        if field_type:
            field_content = f"{field_type}"

    bg_color = ""
    if field_fieldtype == FieldType.REGULAR:
        pass
    elif field_fieldtype == FieldType.BASECLASS:
        bg_color = COLOR_BG_CLASS_INHERIT
    elif field_fieldtype == FieldType.VTABLE:
        bg_color = COLOR_BG_CLASS_VTABLE
    elif field_fieldtype == FieldType.EMPTY:
        bg_color = COLOR_BG_EMPTY

    if bg_color:
        bg_color = f""" bgcolor='{bg_color}'"""

    in_field_port = ""
    if port:
        in_field_port = f""" port='in_{port}'"""
    out_field_port = ""
    if port:
        out_field_port = f""" port='out_{port}'"""

    if position is None:
        position = ""
    if size is None:
        size = ""

    return (
        f"""<tr> <td align="right"{in_field_port}>{position}</td> <td align="right">{size}</td> """
        f"""<td align="left"{bg_color}{out_field_port}>{field_content}</td> </tr>"""
    )
