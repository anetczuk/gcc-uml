#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import io
import logging
from typing import Dict, Any, List
import html

# import subprocess

# import multiprocessing
# from multiprocessing import Pool
# from multiprocessing.pool import ThreadPool as Pool
# from gcclangrawparser.multiprocessingmock import DummyPool as Pool

from showgraph.graphviz import Graph, set_node_style

from gcclangrawparser.langparser import (
    LangContent,
    Entry,
    get_entry_name,
    visit_dump_tree_depth_first,
    DumpTreeNode,
    dump_tree_breadth_first,
)
from gcclangrawparser.io import write_file, read_file


_LOGGER = logging.getLogger(__name__)


def print_html(content: LangContent, out_dir):
    print("writing HTML output to %s", out_dir)
    os.makedirs(out_dir, exist_ok=True)

    depends_dict: Dict[str, List[Any]] = {}
    for entry in content.content_objs.values():
        for entry_field, entry_val in entry.items():
            if entry_field == "_id":
                continue
            if not isinstance(entry_val, Entry):
                continue
            dep_id = entry_val.get_id()
            dep_list = depends_dict.get(dep_id, [])
            dep_list.append((entry_field, entry))
            depends_dict[dep_id] = dep_list

    entries_list = list(content.content_objs.values())
    first_entry = entries_list[0]
    node_tree: DumpTreeNode = dump_tree_breadth_first(first_entry)

    # print_dump_tree(node_tree)

    node_page_gen = NodePageGenerator()
    visit_dump_tree_depth_first(node_tree, node_page_gen.generate_node_page, [depends_dict, out_dir])

    print("writing completed")


class NodePageGenerator:

    def __init__(self):
        self.visited_entries = set()

    def generate_node_page(self, node: DumpTreeNode, args_data):
        depends_dict, out_dir = args_data
        entry = node.entry
        if not isinstance(entry, Entry):
            return True

        entry_id = entry.get_id()
        if entry_id in self.visited_entries:
            # already visited
            return True
        self.visited_entries.add(entry_id)

        graph: Graph = Graph()
        base_graph = graph.base_graph
        base_graph.set_name("use_graph")
        base_graph.set_type("digraph")
        base_graph.set_rankdir("LR")

        main_node_label = f"{entry.get_id()} {entry.get_type()}"
        entry_label = get_entry_label(entry)
        if entry_label:
            main_node_label += f"\n{entry_label}"
        entry_node = graph.addNode(entry.get_id(), shape="box", label=main_node_label)

        entry_node.set("tooltip", main_node_label)
        entry_node.set("href", f"{entry.get_id()}.html")
        style = {"style": "filled", "fillcolor": "red"}
        set_node_style(entry_node, style)

        # create forward edges
        for entry_field, entry_val in entry.items():
            if entry_field == "_id":
                continue
            if entry_field == "_type":
                continue

            if isinstance(entry_val, Entry):
                to_node_id = f"to_{entry_val.get_id()}"
                node_label = f"{entry_val.get_id()} {entry_val.get_type()}"
                entry_label = get_entry_label(entry_val)
                if entry_label:
                    node_label += f"\n{entry_label}"
                next_node = graph.addNode(to_node_id, shape="box", label=node_label)
                if next_node:
                    next_node.set("tooltip", node_label)
                    next_node.set("href", f"{entry_val.get_id()}.html")
                    style = {"style": "filled", "fillcolor": "white"}
                    set_node_style(next_node, style)
                edge = graph.addEdge(entry.get_id(), to_node_id)
            else:
                to_node_id = entry_val.replace(":", "_")
                # to_node_id = entry_val
                next_node = graph.addNode(to_node_id, shape="box", label=entry_val)
                if next_node:
                    style = {"style": "filled", "fillcolor": "#dddddd"}
                    set_node_style(next_node, style)
                edge = graph.addEdge(entry.get_id(), to_node_id)

            edge.set_label(entry_field)  # pylint: disable=E1101

        # create backward edges
        dep_list = depends_dict.get(entry.get_id(), [])
        for dep_field, dep_entry in dep_list:
            from_node_id = f"from_{dep_entry.get_id()}"
            node_label = f"{dep_entry.get_id()} {dep_entry.get_type()}"
            entry_label = get_entry_label(dep_entry)
            if entry_label:
                node_label += f"\n{entry_label}"
            prev_node = graph.addNode(from_node_id, shape="box", label=node_label)
            if prev_node:
                prev_node.set("tooltip", node_label)
                prev_node.set("href", f"{dep_entry.get_id()}.html")
                style = {"style": "filled", "fillcolor": "white"}
                set_node_style(prev_node, style)
            edge = graph.addEdge(from_node_id, entry.get_id())
            edge.set_label(dep_field)  # pylint: disable=E1101

        # img_content = get_graph_as_svg(graph)
        out_svg_file = f"{entry.get_id()}.svg"
        out_svg_path = os.path.join(out_dir, out_svg_file)
        img_content = write_graph_as_svg(graph, out_svg_path)
        # img_content = f"""<img src="{out_svg_file}">"""

        entry_content = print_node(node)

        content = f"""\
<!DOCTYPE HTML>
<!--
File was automatically generated using 'gcc-lang-raw-parser' project.
Project is distributed under the BSD 3-Clause license.
-->
<html>
<head>
    <title>node view {main_node_label}</title>
    <style>
        body {{
                background-color: #bbbbbb;
             }}

        pre {{  background-color: rgb(226, 226, 226);
               margin: 0px;
               padding: 16px;
            }}

        pre code {{  margin: 0px;
                    padding: 0px;
                 }}

        .section {{
            margin-bottom: 12px;
        }}

        .graphsection img {{
        }}

        .entryindent {{
            padding-left: 24px;
        }}

        .missinghandler {{
            background-color: red;
        }}

        .collapsed {{
            display: none;
        }}
    </style>

    <script>
/* jshint esversion: 6 */


function element_click(source) {{
    /// do nothing
}}

function toggle_element(element_id) {{
    let elem = document.getElementById(element_id);
    let elem_class = elem.className
    if (elem_class.includes("collapsed")) {{
        /// expand
        elem_class = elem_class.replace(" collapsed", "");
    }} else {{
        /// collapse
        elem_class += " collapsed";
    }}
    elem.className = elem_class;
}}
    </script>
</head>
<body>
    <div class="section"><a href="@1.html">back to @1</a></div>
    <div class="graphsection section">
{img_content}
    </div>


    <div class="section">
{entry_content}
    </div>
</body>
</html>
"""

        out_file = os.path.join(out_dir, f"{entry.get_id()}.html")
        write_file(out_file, content)
        return True


def print_node(node: DumpTreeNode):
    printer = EntryPrinter()
    visit_dump_tree_depth_first(node, print_single_node, [printer, node])
    return printer.content


def print_single_node(node: DumpTreeNode, args_data=None):
    printer = args_data[0]
    root_node = args_data[1]
    prop = node.property
    if root_node == node:
        prop = None
    printer.print_item(node.entry, node.depth, None, prop)
    return True


class EntryPrinter:
    def __init__(self):
        self.content = ""
        self.recent_depth = -1
        self.elem_id_counter = 0

    def print_item(self, entry, depth, _parent: Entry, prop: str):
        for _ in range(depth, self.recent_depth + 1):
            self.content += "</div>\n"
        self.recent_depth = depth

        self.elem_id_counter += 1
        indent_id = f"""indent_{self.elem_id_counter}"""
        prefix_content = f"""<span onclick='toggle_element("{indent_id}");'>{prop}:</span> """
        if prop is None:
            prefix_content = ""
        # parent_id = None
        # if _parent:
        #     parent_id = _parent.get_id()
        # self.content += f"<!-- parent: {parent_id} -->\n"
        self.content += print_head(entry, prefix_content=prefix_content)
        self.content += f"""<div id="{indent_id}" class="entryindent">\n"""

        if isinstance(entry, Entry):
            if entry.get_type() == "function_decl":
                entry_name = get_entry_name(entry)
                if entry_name.startswith("__"):
                    # internal function - do not go deeper
                    return False
        return True


def print_head(entry, prefix_content="", postfix_content="", print_label=False):
    if not isinstance(entry, Entry):
        entry_value = escape_html(entry)
        return f"""<div class="entryhead">{prefix_content}{entry_value}{postfix_content}</div>\n"""
    label_content = ""
    if print_label:
        label_content = " " + get_entry_label(entry)
    return f"""<div class="entryhead">{prefix_content}{entry.get_type()} {get_entry_id_href(entry)}" \
        "{label_content}{postfix_content}</div>\n"""


def get_entry_id_href(entry: Entry):
    entry_id = entry.get_id()
    return f"""<a href="{entry_id}.html">{entry_id}</a>"""


def escape_html(content: str) -> str:
    return html.escape(content)


## ====================================================


def get_entry_label(entry):
    # if entry.get_type() == "identifier_node":
    #     return get_entry_name(entry)
    # if entry.get_type() == "translation_unit_decl":
    #     return get_entry_name(entry)
    # if entry.get_type() == "namespace_decl":
    #     return get_entry_name(entry)
    # if entry.get_type() == "function_decl":
    #     return get_entry_name(entry)
    # return None
    return get_entry_name(entry)


def write_graph_as_svg(graph: Graph, out_svg_path):
    out_dot_path = f"{out_svg_path}.dot"
    svg_dot_content = read_file(out_dot_path)
    curr_dot = graph.toString()
    if svg_dot_content == curr_dot:
        return read_file(out_svg_path)
    graph.write(out_svg_path, file_format="svg")
    write_file(out_dot_path, curr_dot)
    return read_file(out_svg_path)


def get_graph_as_svg(graph: Graph):
    with io.BytesIO() as buffer:
        # graph.write(buffer, file_format="raw")
        # dot_contents = buffer.getvalue()
        # dot_contents_str = dot_contents.decode("utf-8")
        # return convert_dot(dot_contents_str)

        # TODO: operation takes very long - optimize it
        graph.write(buffer, file_format="svg")
        dot_contents = buffer.getvalue()
        return dot_contents.decode("utf-8")


# def convert_dot(content: str):
#     # convert to svg
#     svg = subprocess.run(
#         "dot -Tsvg", shell=True, stdout=subprocess.PIPE, input=content.encode()
#     ).stdout.decode()
#     return svg
