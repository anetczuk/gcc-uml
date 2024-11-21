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

from multiprocessing import Pool as Pool1
# from multiprocessing.pool import ThreadPool as Pool1

# from gcclangrawparser.multiprocessingmock import DummyPool as Pool1

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
    get_node_entry_id,
    is_entry_prop_internal,
)
from gcclangrawparser.io import write_file, read_file
from gcclangrawparser.abstracttraversal import get_nodes_from_tree_ancestors


_LOGGER = logging.getLogger(__name__)


def print_html(content: LangContent, out_dir, generate_page_graph=True):
    _LOGGER.info("writing HTML output to %s", out_dir)
    os.makedirs(out_dir, exist_ok=True)

    depends_dict: Dict[str, List[Any]] = {}
    for entry in content.content_objs.values():
        for entry_field, entry_val in entry.items():
            if is_entry_prop_internal(entry_field):
                continue
            if not isinstance(entry_val, Entry):
                continue
            dep_id = entry_val.get_id()
            dep_list = depends_dict.get(dep_id, [])
            dep_list.append((entry_field, entry))
            depends_dict[dep_id] = dep_list

    _LOGGER.info("converting %s entries to tree", content.size())
    entry_tree: EntryTreeNode = get_entry_tree(content, include_internals=False)
    # entry_tree: EntryTreeNode = get_entry_tree(content, include_internals=True)

    # tree_content = print_entry_tree(entry_tree)
    # print("tree:", tree_content)

    # generate pages
    generate_content_node(entry_tree, depends_dict, out_dir, generate_page_graph)

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
        if is_entry_prop_internal(entry_prop):
            continue
        add_hyperlink = True
        if not include_internals:
            if is_entry_language_internal(entry_val):
                add_hyperlink = False
        entry_graph.add_edge_forward(entry, entry_val, entry_prop, with_hyperlink=add_hyperlink, to_node_prefix="to_")

    # create backward edges
    dep_list = depends_dict.get(entry.get_id(), [])
    for entry_prop, dep_entry in dep_list:
        add_hyperlink = True
        if not include_internals:
            if is_entry_language_internal(dep_entry):
                add_hyperlink = False
        entry_graph.add_edge_backward(
            dep_entry, entry, entry_prop, with_hyperlink=add_hyperlink, from_node_prefix="from_"
        )
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

    def add_node(self, entry: Entry, entry_color=False, with_hyperlink=True, name_prefix=None) -> str:
        if not isinstance(entry, Entry):
            return self.add_node_value(entry)

        node_id = self._get_entry_id(entry)
        if name_prefix:
            node_id = name_prefix + node_id
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

    def add_node_value(self, entry, name_prefix=None) -> str:
        node_id = self._value_entry_counter
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
            to_node_id = self.add_node(to_entry, with_hyperlink=with_hyperlink, name_prefix=to_node_prefix)
        else:
            to_node_id = self.add_node_value(to_entry, name_prefix=to_node_prefix)
        # print("adding edge:", from_node_id, "->", to_node_id, from_entry, to_entry)
        self.connect_nodes(from_node_id, to_node_id, prop)

    def add_edge_backward(self, from_entry, to_entry, prop, with_hyperlink=True, from_node_prefix=None):
        from_node_id = None
        if isinstance(from_entry, Entry):
            from_node_id = self.add_node(from_entry, with_hyperlink=with_hyperlink, name_prefix=from_node_prefix)
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

    def _get_entry_id(self, entry: Entry) -> str:
        if isinstance(entry, Entry):
            return str(id(entry))
        return entry.replace(":", "_")


def generate_content_node(entry_tree, depends_dict, out_dir, generate_page_graph):
    traversal = EntryTreeDepthFirstTraversal()
    node_list = get_nodes_from_tree_ancestors(entry_tree, traversal, bottom_top=True)
    node_list = filter_repeated_entries(node_list)

    # tree_content = print_entry_tree(entry_tree)
    # print("tree:", tree_content)

    # generate_content_list(node_list, depends_dict, out_dir, generate_page_graph)

    process_num = os.cpu_count()

    with Pool1(process_num) as process_pool:
        result_queue = []
        node_list_size = len(node_list)
        chunk_size = int(node_list_size / process_num) + 1
        _LOGGER.info("nodes num: %s chunk size: %s", node_list_size, chunk_size)

        chunks_list = list( chunks(node_list, chunk_size) )

        for chunk_item in chunks_list:
            async_result = process_pool.apply_async(
                generate_content_list, [chunk_item, depends_dict, out_dir, generate_page_graph]
            )
            result_queue.append(async_result)

        _LOGGER.info("waiting for processes to finish")

        # wait for results
        for async_result in result_queue:
            async_result.get()


def generate_content_list(node_list, depends_dict, out_dir, generate_page_graph):
    node_page_gen = NodePageGenerator(include_internals=True, generate_page_graph=generate_page_graph)
    node_page_gen.generate_from_list(node_list, depends_dict, out_dir)


def chunks(data_list, chunk_size):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]


def filter_repeated_entries(node_list):
    ret_list = []
    visited_entries = set()
    for ancestors_list in node_list:
        node = ancestors_list[-1]
        entry = node.entry
        if not isinstance(entry, Entry):
            continue
        entry_id = entry.get_id()
        if entry_id in visited_entries:
            # already visited
            if not node.items:
                continue
        visited_entries.add(entry_id)
        ret_list.append(ancestors_list)
    return ret_list


class NodePageGenerator:

    def __init__(self, include_internals=False, generate_page_graph=True):
        self.include_internals = include_internals
        self.generate_page_graph = generate_page_graph
        self.node_printer = NodePrinter(include_internals)

    def generate_from_tree(self, entry_tree: EntryTreeNode, depends_dict, out_dir):
        traversal = EntryTreeDepthFirstTraversal()
        node_list = get_nodes_from_tree_ancestors(entry_tree, traversal, bottom_top=True)
        self.generate_from_list(node_list, depends_dict, out_dir)

    def generate_from_list(self, node_list, depends_dict, out_dir):
        # list_size = len(node_list)
        for ancestors_list in node_list:
        # for index, ancestors_list in enumerate(node_list):
            # node: EntryTreeNode = ancestors_list[-1]
            # node_id = get_node_entry_id(node)
            # if index % 100 == 0:
            #     _LOGGER.info("generating page %s / %s for %s", index, list_size, node_id)
            self.generate_node_page(ancestors_list, depends_dict, out_dir)

    # def generate_list_content(self, node_list, depends_dict, out_dir):
    #     gen_context = [depends_dict, out_dir]
    #     for ancestors_list in node_list:
    #         self.generate_node_page(ancestors_list, None, gen_context)

    def generate_node_page(self, ancestors_list, depends_dict, out_dir):
        node = ancestors_list[-1]
        entry = node.entry

        img_content = ""
        if self.generate_page_graph:
            graph = generate_entry_local_graph(entry, depends_dict, include_internals=self.include_internals)

            img_content = get_graph_as_svg(graph)
            # out_svg_file = f"{entry.get_id()}.svg"
            # out_svg_path = os.path.join(out_dir, out_svg_file)
            # img_content = write_graph_as_svg(graph, out_svg_path)
            # # img_content = f"""<img src="{out_svg_file}">"""

        entry_content = self.node_printer.print_node(node)

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

function toggle_element(element) {{
    let next_elem = element.parentElement;
    next_elem = next_elem.nextSibling;
    while ( next_elem.tagName != "DIV" ) {{
        next_elem = next_elem.nextSibling;
        if ( next_elem == null ) {{
            return ;
        }}
    }}

    let elem_class = next_elem.className
    if (elem_class.includes("entryindent") == false) {{
        /// console.error("unable to find element to collapse/expand");
        return;
    }}

    if (elem_class.includes("collapsed")) {{
        /// expand
        elem_class = elem_class.replace(" collapsed", "");
    }} else {{
        /// collapse
        elem_class += " collapsed";
    }}
    next_elem.className = elem_class;
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


class NodePrinter:
    def __init__(self, include_internals=False):
        self.include_internals = include_internals
        self.node_fields_content = {}
        self.entry_printer = EntryPrinter(include_internals)

    def generate_content(self, tree: List[EntryTreeNode]):
        pass

    def print_node(self, node: EntryTreeNode):
        # return self.print_node_single(node)
        return self.print_node_old(node)
        # return self.print_node_recursive(node, None)

    def print_node_single(self, node: EntryTreeNode):
        node_id = get_node_entry_id(node)
        node_content = self.node_fields_content.get(node_id)
        if node_content is not None:
            head = self.entry_printer.print_head(node.entry, None)
            return head + node_content

        content = ""
        head = self.entry_printer.print_head(node.entry, None)
        content += head

        items_content = """<div class="entryindent">\n"""
        for node_item in node.items:
            items_content += self._print_node_sub(node_item, node_item.property)
        items_content += """</div>\n"""

        if node_id is not None and node.items:
            self.node_fields_content[node_id] = items_content

        return content + items_content

    def _print_node_sub(self, node: EntryTreeNode, prop):
        node_entry = node.entry
        if not isinstance(node_entry, Entry):
            head = self.entry_printer.print_head(node_entry, prop)
            return head

        node_id = get_node_entry_id(node)
        node_content = self.node_fields_content.get(node_id)
        if node_content is None:
            # entry_id = self.get_id(node)
            # raise RuntimeError(f"unable to get node content: {entry_id}")
            head = self.entry_printer.print_head(node_entry, prop)
            return head

        head = self.entry_printer.print_head(node_entry, prop)
        return head + node_content

    def print_node_recursive(self, node: EntryTreeNode, prop):
        content = ""
        head = self.entry_printer.print_head(node.entry, prop)
        content += head

        items_content = None
        entry_id = self.get_id(node)
        if entry_id is not None:
            items_content = self.node_fields_content.get(entry_id)

        if items_content is None:
            items_content = """<div class="entryindent">\n"""

            for node_item in node.items:
                items_content += self.print_node_recursive(node_item, node_item.property)

            items_content += """</div>\n"""

            if entry_id is not None:
                self.node_fields_content[entry_id] = content

        content += items_content
        return content

    def get_id(self, node: EntryTreeNode):
        return get_node_entry_id(node)

    def print_node_old(self, node: EntryTreeNode):
        printer = EntryPrinter(include_internals=self.include_internals)
        EntryTreeDepthFirstTraversal.traverse(node, self._print_single_node, [printer, node])
        printer.close_sections()
        return printer.content

    def _print_single_node(self, ancestors_list: EntryTreeNode, _node_data=None, visitor_context=None):
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
        head = self.print_head(entry, prop)

        self.content += head
        self.content += """<div class="entryindent">\n"""
        return True

    def print_head(self, entry, prop):
        prefix_content = f"""<span onclick='toggle_element(this);'>{prop}:</span> """
        if prop is None:
            prefix_content = ""
        head = print_head(entry, prefix_content=prefix_content, print_label=True)
        return head

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
