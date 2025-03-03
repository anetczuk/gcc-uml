#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import io
import logging
from typing import Any, Dict
import json

from showgraph.graphviz import Graph, set_node_style

from gccuml.langcontent import (
    Entry,
    get_entry_name,
    EntryTreeDepthFirstTraversal,
    print_entry_tree,
    EntryTree,
    LangContent,
)
from gccuml.io import write_file, read_file
from gccuml.langparser import parse_raw


_LOGGER = logging.getLogger(__name__)


def process_tools_config(config: Dict[Any, Any]):
    input_files = config.get("inputfiles")
    if not input_files:
        raise RuntimeError("no input files given")
    raw_file_path = input_files[-1]
    _LOGGER.info("parsing input file %s", raw_file_path)
    reduce_paths = config.get("reducepaths", False)
    content: LangContent = parse_raw(raw_file_path, reduce_paths)
    if content is None:
        raise RuntimeError(f"unable to parse {raw_file_path}")

    out_types_fields = config["outtypefields"]
    if out_types_fields:
        _LOGGER.info("dumping types dict")
        types_fields = content.get_types_fields()
        types_str = json.dumps(types_fields, indent=4)
        write_file(out_types_fields, types_str)

    include_internals = config["includeinternals"]
    entry_tree: EntryTree = EntryTree(content)
    entry_tree.generate_tree(include_internals=include_internals, depth_first=False)

    if config["outtreetxt"]:
        _LOGGER.info("dumping nodes text representation to %s", config["outtreetxt"])
        write_entry_tree(entry_tree, config["outtreetxt"])

    if config["outbiggraph"]:
        _LOGGER.info("dumping nodes dot representation to %s", config["outbiggraph"])
        generate_big_graph(entry_tree, config["outbiggraph"])


def write_entry_tree(entry_tree: EntryTree, out_path, indent=2):
    tree_root = entry_tree.get_tree_root()
    tree_content = print_entry_tree(tree_root, indent)
    write_file(out_path, tree_content)


def generate_big_graph(entry_tree: EntryTree, out_path):
    tree_root = entry_tree.get_tree_root()
    # print_entry_tree(tree_root)
    nodes_list = EntryTreeDepthFirstTraversal.to_list(tree_root)

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


class EntryDotGraph:

    def __init__(self):
        self.graph: Graph = Graph()
        base_graph = self.graph.base_graph
        base_graph.set_name("use_graph")
        base_graph.set_type("digraph")
        # base_graph.set_rankdir("LR")
        self._value_entry_counter: int = 0

    def get_base_graph(self):
        return self.graph.base_graph

    def add_node(self, entry: Entry, entry_color=False, with_hyperlink=True, name_prefix=None) -> str:
        if not isinstance(entry, Entry):
            return self.add_node_value(entry)

        node_id = self._get_entry_id(entry)
        if name_prefix:
            node_id = name_prefix + node_id
        node_label = self._get_entry_label(entry)
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

    def add_node_value(self, entry: Any, name_prefix: str = None) -> str:
        node_id: str = str(self._value_entry_counter)
        if name_prefix:
            node_id = name_prefix + str(node_id)
        self._value_entry_counter += 1
        # print("adding value node:", node_id, entry)
        entry_node = self.graph.addNode(node_id, shape="box", label=entry)
        entry_node.set("tooltip", f"{entry}'")
        style = {"style": "filled", "fillcolor": "#dddddd"}
        set_node_style(entry_node, style)
        return node_id

    def add_edge_forward(self, from_entry, to_entry, prop, with_hyperlink=True, to_node_prefix=None):
        from_node_id = self._get_entry_id(from_entry)
        to_node_id = None
        if isinstance(to_entry, Entry):
            if with_hyperlink:
                to_node_id = self.add_node(to_entry, with_hyperlink=with_hyperlink, name_prefix=to_node_prefix)
            else:
                node_label = self._get_entry_label(to_entry)
                to_node_id = self.add_node_value(node_label, name_prefix=to_node_prefix)
        else:
            to_node_id = self.add_node_value(to_entry, name_prefix=to_node_prefix)
        # print("adding edge:", from_node_id, "->", to_node_id, from_entry, to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def add_edge_backward(self, from_entry, to_entry, prop, with_hyperlink=True, from_node_prefix=None):
        from_node_id = None
        if isinstance(from_entry, Entry):
            if with_hyperlink:
                from_node_id = self.add_node(from_entry, with_hyperlink=with_hyperlink, name_prefix=from_node_prefix)
            else:
                node_label = self._get_entry_label(from_entry)
                from_node_id = self.add_node_value(node_label, name_prefix=from_node_prefix)
        else:
            from_node_id = self.add_node_value(from_entry, name_prefix=from_node_prefix)
        to_node_id = self._get_entry_id(to_entry)
        # print("adding edge:", from_node_id, "->", to_node_id, from_entry, to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def connect_entries(self, from_entry, to_entry, prop):
        from_node_id = self._get_entry_id(from_entry)
        to_node_id = self._get_entry_id(to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def connect_nodes(self, from_node_id, to_node_id, prop):
        edge = self.graph.addEdge(from_node_id, to_node_id, create_nodes=True)
        if edge is None:
            raise RuntimeError("edge already exists")
        edge.set_label(prop)  # pylint: disable=E1101

    def _get_entry_label(self, entry: Entry) -> str:
        node_label = f"{entry.get_id()} {entry.get_type()}"
        entry_label = get_entry_name(entry)
        if entry_label:
            node_label += f"\n{entry_label}"
        return node_label

    def _get_entry_id(self, entry: Entry) -> str:
        if isinstance(entry, Entry):
            return str(id(entry))
        return entry.replace(":", "_")


## ====================================================


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
