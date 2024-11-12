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

from showgraph.graphviz import Graph, set_node_style

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    get_entry_name,
    EntryTreeNode,
    get_entry_tree,
    EntryTreeDepthFirstTraversal,
    print_entry_tree,
    is_entry_language_internal,
)
from gcclangrawparser.io import write_file, read_file


_LOGGER = logging.getLogger(__name__)


def print_html(content: LangContent, out_dir):
    _LOGGER.info("writing HTML output to %s", out_dir)
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

    _LOGGER.info("converting %s entries to tree", content.size())
    entry_tree: EntryTreeNode = get_entry_tree(content, include_internals=False)

    # print_entry_tree(entry_tree)

    # generate pages

    # traversal = EntryTreeDepthFirstTraversal()
    # node_list = get_nodes_from_tree_ancestors(entry_tree, traversal)

    node_page_gen = NodePageGenerator(include_internals=True)
    EntryTreeDepthFirstTraversal.traverse(entry_tree, node_page_gen.generate_node_page, [depends_dict, out_dir])

    _LOGGER.info("writing completed")


def write_entry_tree(content: LangContent, out_path, indent=2):
    entry_tree: EntryTreeNode = get_entry_tree(content, include_internals=False)
    tree_content = print_entry_tree(entry_tree, indent)
    write_file(out_path, tree_content)


def generate_big_graph(content: LangContent, out_path):
    entry_tree: EntryTreeNode = get_entry_tree(content, include_internals=False)
    # print_entry_tree(entry_tree)
    nodes_list = EntryTreeDepthFirstTraversal.to_list(entry_tree)

    entry_graph = EntryDotGraph()

    # add nodes
    for item in nodes_list:
        node = item[0]
        entry = node.entry
        if isinstance(entry, Entry):
            entry_graph.add_node(entry)

    # add edges
    for item in nodes_list:
        node = item[0]
        entry = node.entry

        for child_node in node.items:
            child_entry = child_node.entry
            prop = child_node.property
            entry_graph.add_edge_forward(entry, child_entry, prop)

    entry_graph.graph.write(out_path, file_format="png")


def generate_entry_local_graph(entry, depends_dict, include_internals=True):
    entry_graph = EntryDotGraph()
    entry_graph.get_base_graph().set_rankdir("LR")
    entry_graph.add_node(entry, "red")

    # create forward edges
    for entry_prop, entry_val in entry.items():
        if entry_prop == "_id":
            continue
        if entry_prop == "_type":
            continue
        add_hyperlink = True
        if not include_internals:
            if is_entry_language_internal(entry_val):
                add_hyperlink = False
        entry_graph.add_edge_forward(entry, entry_val, entry_prop, with_hyperlink=add_hyperlink)

    # create backward edges
    dep_list = depends_dict.get(entry.get_id(), [])
    for entry_prop, dep_entry in dep_list:
        add_hyperlink = True
        if not include_internals:
            if is_entry_language_internal(dep_entry):
                add_hyperlink = False
        entry_graph.add_edge_backward(dep_entry, entry, entry_prop, with_hyperlink=add_hyperlink)
    graph = entry_graph.graph

    return graph


class EntryDotGraph:

    def __init__(self):
        self.graph: Graph = Graph()
        base_graph = self.graph.base_graph
        base_graph.set_name("use_graph")
        base_graph.set_type("digraph")
        # base_graph.set_rankdir("LR")
        self._value_entry_counter = 0

    def get_base_graph(self):
        return self.graph.base_graph

    def add_node(self, entry: Entry, entry_color=False, with_hyperlink=True) -> str:
        if not isinstance(entry, Entry):
            return self.add_node_value(entry)

        node_id = self._get_node_id(entry)
        node_label = f"{entry.get_id()} {entry.get_type()}"
        entry_label = get_entry_label(entry)
        if entry_label:
            node_label += f"\n{entry_label}"
        # print("adding entry node:", node_id, entry.get_id())
        entry_node = self.graph.addNode(node_id, shape="box", label=node_label)
        if entry_node is None:
            # node already added
            return node_id
            # raise RuntimeError(f"entry {entry.get_id()} already added")
        entry_node.set("tooltip", node_label)
        if with_hyperlink:
            entry_node.set("href", f"{entry.get_id()}.html")
        if entry_color:
            style = {"style": "filled", "fillcolor": "red"}
            set_node_style(entry_node, style)
        return node_id

    def add_node_value(self, entry) -> str:
        node_id = self._value_entry_counter
        self._value_entry_counter += 1
        # print("adding value node:", node_id, entry)
        entry_node = self.graph.addNode(node_id, shape="box", label=entry)
        entry_node.set("tooltip", f"{entry}'")
        style = {"style": "filled", "fillcolor": "#dddddd"}
        set_node_style(entry_node, style)
        return node_id

    def add_edge_forward(self, from_entry, to_entry, prop, with_hyperlink=True):
        from_node_id = self._get_node_id(from_entry)
        to_node_id = None
        if isinstance(to_entry, Entry):
            to_node_id = self.add_node(to_entry, with_hyperlink=with_hyperlink)
        else:
            to_node_id = self.add_node_value(to_entry)
        # print("adding edge:", from_node_id, "->", to_node_id, from_entry, to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def add_edge_backward(self, from_entry, to_entry, prop, with_hyperlink=True):
        from_node_id = None
        if isinstance(from_entry, Entry):
            from_node_id = self.add_node(from_entry, with_hyperlink=with_hyperlink)
        else:
            from_node_id = self.add_node_value(from_entry)
        to_node_id = self._get_node_id(to_entry)
        # print("adding edge:", from_node_id, "->", to_node_id, from_entry, to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def connect_entries(self, from_entry, to_entry, prop):
        from_node_id = self._get_node_id(from_entry)
        to_node_id = self._get_node_id(to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def connect_nodes(self, from_node_id, to_node_id, prop):
        edge = self.graph.addEdge(from_node_id, to_node_id, create_nodes=True)
        if edge is None:
            raise RuntimeError("edge already exists")
        edge.set_label(prop)  # pylint: disable=E1101

    def _get_node_id(self, entry: Entry) -> str:
        if isinstance(entry, Entry):
            return str(id(entry))
        return entry.replace(":", "_")


class NodePageGenerator:

    def __init__(self, include_internals=False):
        self.include_internals = include_internals
        self.visited_entries = set()

    def generate_node_page(self, ancestors_list, _node_data, gen_context=None):
        node = ancestors_list[-1]
        entry = node.entry
        if not isinstance(entry, Entry):
            return True

        entry_id = entry.get_id()
        if entry_id in self.visited_entries:
            # already visited
            return True
        # _LOGGER.info("generating page for %s", entry_id)
        self.visited_entries.add(entry_id)

        depends_dict, out_dir = gen_context
        graph = generate_entry_local_graph(entry, depends_dict, include_internals=self.include_internals)

        img_content = get_graph_as_svg(graph)
        # out_svg_file = f"{entry.get_id()}.svg"
        # out_svg_path = os.path.join(out_dir, out_svg_file)
        # img_content = write_graph_as_svg(graph, out_svg_path)
        # # img_content = f"""<img src="{out_svg_file}">"""

        entry_content = print_node(node, include_internals=self.include_internals)

        main_node_label = f"{entry.get_id()} {entry.get_type()}"

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


def print_node(node: EntryTreeNode, include_internals=False):
    printer = EntryPrinter(include_internals=include_internals)
    EntryTreeDepthFirstTraversal.traverse(node, print_single_node, [printer, node])
    printer.close_sections()
    return printer.content


def print_single_node(ancestors_list: EntryTreeNode, _node_data=None, visitor_context=None):
    node = ancestors_list[-1]
    if not _node_data:
        _node_data = 0
    printer, root_node = visitor_context
    prop = node.property
    if root_node == node:
        prop = None
    parent = None
    if len(ancestors_list) > 1:
        parent = ancestors_list[-2]
        parent = parent.entry
    node_level = len(ancestors_list) - 1
    printer.print_item(node.entry, node_level, parent, prop)
    return True


class EntryPrinter:
    def __init__(self, include_internals=False):
        self.include_internals = include_internals
        self.content = ""
        self.recent_depth = -1
        self.elem_id_counter = 0

    def print_item(self, entry, level, _parent: Entry, prop: str):
        if not self.include_internals:
            if is_entry_language_internal(entry):
                # internal function - do not go deeper
                return False

        self.close_sections(level)

        self.elem_id_counter += 1
        indent_id = f"""indent_{self.elem_id_counter}"""
        # par_id = None
        # if _parent:
        #     par_id = _parent.get_id()
        prefix_content = f"""<span onclick='toggle_element("{indent_id}");'>{prop}:</span> """
        if prop is None:
            prefix_content = ""
        # parent_id = None
        # if _parent:
        #     parent_id = _parent.get_id()
        # self.content += f"<!-- parent: {parent_id} -->\n"
        self.content += print_head(entry, prefix_content=prefix_content, print_label=True)
        self.content += f"""<div id="{indent_id}" class="entryindent">\n"""
        return True

    def close_sections(self, level=0):
        for _ in range(level, self.recent_depth + 1):
            self.content += "</div>\n"
        self.recent_depth = level


def print_head(entry, prefix_content="", postfix_content="", print_label=False):
    if not isinstance(entry, Entry):
        entry_value = escape_html(entry)
        return f"""<div class="entryhead">{prefix_content}{entry_value}{postfix_content}</div>\n"""
    label_content = ""
    if print_label:
        label_content = " " + get_entry_label(entry)
    return (
        f"""<div class="entryhead">{prefix_content}{entry.get_type()} {get_entry_id_href(entry)}"""
        f"""{label_content}{postfix_content}</div>\n"""
    )


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
    if graph is None:
        return None
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
