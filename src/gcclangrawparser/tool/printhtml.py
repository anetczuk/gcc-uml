#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict, Any, List
import html
import shutil

from multiprocessing import Pool as Pool1

# from multiprocessing.pool import ThreadPool as Pool1

# from gcclangrawparser.multiprocessingmock import DummyPool as Pool1

from gcclangrawparser.langcontent import (
    Entry,
    get_entry_name,
    EntryTreeNode,
    EntryTreeDepthFirstTraversal,
    is_entry_language_internal,
    is_entry_prop_internal,
    EntryTree,
)
from gcclangrawparser.io import write_file
from gcclangrawparser.vizjs import DATA_DIR
from gcclangrawparser.tool.tools import EntryDotGraph, get_graph_as_svg
from gcclangrawparser.progressbar import get_processbar_pool, iterate_progressar, end_progressbar


_LOGGER = logging.getLogger(__name__)


def print_html(entry_tree: EntryTree, out_dir, generate_page_graph=True, use_vizjs=True, jobs=None):
    _LOGGER.info("writing HTML output to %s", out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print_html_pages(entry_tree, out_dir, generate_page_graph, use_vizjs, jobs=jobs)
    _LOGGER.info("writing completed")


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


def print_html_pages(entry_tree: EntryTree, out_dir, generate_page_graph, use_vizjs, jobs=None):
    content = entry_tree.content
    include_internals = entry_tree.include_internals

    depends_dict: Dict[str, List[Any]] = content.get_parents_dict()

    _LOGGER.info("converting %s entries to tree", content.size())

    # tree_content = print_entry_tree(tree_root)
    # print("tree:", tree_content)

    node_list = entry_tree.get_filtered_nodes()
    # random.shuffle(node_list)

    # tree_content = print_entry_tree(tree_root)
    # print("tree:", tree_content)

    if generate_page_graph and use_vizjs:
        vizjs_path = os.path.join(DATA_DIR, "viz-standalone.js")
        shutil.copy(vizjs_path, out_dir, follow_symlinks=True)

    if jobs is None:
        jobs = os.cpu_count()
        jobs = int(jobs * 2 / 3) + 1

    elif jobs < 2:
        node_list_size = len(node_list)
        _LOGGER.info("nodes num: %s", node_list_size)
        generate_content_list(node_list, depends_dict, out_dir, generate_page_graph, use_vizjs)
        return

    process_num = jobs

    with get_processbar_pool(Pool1, process_num) as process_pool:
        # with Pool1(process_num) as process_pool:

        result_queue = []
        node_list_size = len(node_list)
        chunk_size = int(node_list_size / process_num) + 1
        _LOGGER.info("nodes num: %s chunk size: %s", node_list_size, chunk_size)

        chunks_list = chunks_equal(node_list, process_num)
        # chunks_list = list(chunks(node_list, chunk_size))

        for proc_index, chunk_item in enumerate(chunks_list):
            async_result = process_pool.apply_async(
                generate_content_list,
                [chunk_item, depends_dict, out_dir, generate_page_graph, use_vizjs, include_internals, proc_index],
            )
            result_queue.append(async_result)

        _LOGGER.info("waiting for processes to finish")

        # wait for results
        for async_result in result_queue:
            async_result.get()


def generate_content_list(
    node_list, depends_dict, out_dir, generate_page_graph, use_vizjs, include_internals=False, proc_index=0
):
    node_page_gen = NodePageGenerator(
        include_internals=include_internals, generate_page_graph=generate_page_graph, use_vizjs=use_vizjs
    )
    # node_page_gen.generate_from_list(node_list, depends_dict, out_dir)

    name = f"job {proc_index + 1}"

    for ancestors_list in iterate_progressar(node_list, name, len(node_list)):
        node_page_gen.generate_node_page(ancestors_list, depends_dict, out_dir)
    end_progressbar()

    # for ancestors_list in node_list:
    #     node_page_gen.generate_node_page(ancestors_list, depends_dict, out_dir)


def chunks_equal(nodes_list, chunks_num):
    count_list = []
    for _ in range(0, chunks_num):
        count_list.append([0, []])

    for ancestors_list in nodes_list:
        node = ancestors_list[-1]
        tree_list = EntryTreeDepthFirstTraversal.to_list(node)
        items_count = len(tree_list)
        data_pair = count_list[0]
        data_pair[0] += items_count
        data_pair[1].append(ancestors_list)
        count_list.sort(key=lambda data_pair: data_pair[0])  ## sort by count

    _LOGGER.info("found chunks: %s", [len(item[1]) for item in count_list])
    return [item[1] for item in count_list]


def chunks(data_list, chunk_size):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i : i + chunk_size]


class NodePageGenerator:

    def __init__(self, include_internals=False, generate_page_graph=True, use_vizjs=True):
        self.include_internals = include_internals
        self.generate_page_graph = generate_page_graph
        self.use_vizjs = use_vizjs
        self.node_printer = NodePrinter(include_internals)

    # def generate_from_tree(self, entry_tree: EntryTreeNode, depends_dict, out_dir):
    #     traversal = EntryTreeDepthFirstTraversal()
    #     node_list = get_nodes_from_tree_ancestors(entry_tree, traversal, bottom_top=True)
    #     self.generate_from_list(node_list, depends_dict, out_dir)

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

        graph_scripts = """\
    <script>
        function load_graph() {{
            /// do nothing
        }}
    </script>
"""
        graph_img_content = ""

        if self.generate_page_graph:
            graph = generate_entry_local_graph(entry, depends_dict, include_internals=self.include_internals)

            if self.use_vizjs:
                graph_text = graph.toString()

                graph_scripts = f"""\
    <script src="viz-standalone.js"></script>
    <script>
        function load_graph() {{
            const dot_content = `{graph_text}`;

            Viz.instance().then(function(viz) {{
                var svg = viz.renderSVGElement(dot_content);
                var graph_tag = document.getElementById("graph");
                graph_tag.innerHTML = '';    /// remove all children
                graph_tag.appendChild(svg);
            }});
        }}
    </script>
"""
                graph_img_content = "<span>Refresh page to load graph.</span>"

            else:
                graph_img_content = get_graph_as_svg(graph)
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

{graph_scripts}

</head>
<body onload="load_graph()">
    <div class="section"><a href="@1.html">back to @1</a></div>
    <div id="graph" class="graphsection section">
{graph_img_content}
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
        # self.node_fields_content = {}
        # self.entry_printer = EntryPrinter(include_internals)

    def print_node(self, node: EntryTreeNode):
        # return self.print_node_single(node)
        return self.print_node_old(node)
        # return self.print_node_recursive(node, None)

    # def print_node_single(self, node: EntryTreeNode):
    #     node_id = get_node_entry_id(node)
    #     node_content = self.node_fields_content.get(node_id)
    #     if node_content is not None:
    #         head = self.entry_printer.print_head(node.entry, None)
    #         return head + node_content
    #
    #     content = ""
    #     head = self.entry_printer.print_head(node.entry, None)
    #     content += head
    #
    #     items_content = """<div class="entryindent">\n"""
    #     for node_item in node.items:
    #         items_content += self._print_node_sub(node_item, node_item.property)
    #     items_content += """</div>\n"""
    #
    #     if node_id is not None and node.items:
    #         self.node_fields_content[node_id] = items_content
    #
    #     return content + items_content
    #
    # def _print_node_sub(self, node: EntryTreeNode, prop):
    #     node_entry = node.entry
    #     if not isinstance(node_entry, Entry):
    #         head = self.entry_printer.print_head(node_entry, prop)
    #         return head
    #
    #     node_id = get_node_entry_id(node)
    #     node_content = self.node_fields_content.get(node_id)
    #     if node_content is None:
    #         # entry_id = get_node_entry_id(node)
    #         # raise RuntimeError(f"unable to get node content: {entry_id}")
    #         head = self.entry_printer.print_head(node_entry, prop)
    #         return head
    #
    #     head = self.entry_printer.print_head(node_entry, prop)
    #     return head + node_content

    ## faild because of stack overflow
    # def print_node_recursive(self, node: EntryTreeNode, prop):
    #     content = ""
    #     head = self.entry_printer.print_head(node.entry, prop)
    #     content += head
    #
    #     items_content = None
    #     entry_id = get_node_entry_id(node)
    #     if entry_id is not None:
    #         items_content = self.node_fields_content.get(entry_id)
    #
    #     if items_content is None:
    #         items_content = """<div class="entryindent">\n"""
    #
    #         for node_item in node.items:
    #             items_content += self.print_node_recursive(node_item, node_item.property)
    #
    #         items_content += """</div>\n"""
    #
    #         if entry_id is not None:
    #             self.node_fields_content[entry_id] = content
    #
    #     content += items_content
    #     return content

    def print_node_old(self, node: EntryTreeNode):
        printer = EntryPrinter(include_internals=self.include_internals)
        EntryTreeDepthFirstTraversal.traverse(node, self._print_single_node, [printer, node])
        printer.close_sections()
        return printer.get_content()

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
        return printer.print_item(node.entry, node_level, parent, prop)


class EntryPrinter:
    def __init__(self, include_internals=False):
        self.include_internals = include_internals
        self.content_list = []
        self.recent_depth = -1

    def get_content(self):
        return "".join(self.content_list)

    def print_item(self, entry, level, _parent: Entry, prop: str):
        if not self.include_internals:
            if is_entry_language_internal(entry):
                # internal function - do not go deeper
                return False

        self.close_sections(level)
        head = self.print_head(entry, prop)

        self.content_list.append(head)
        self.content_list.append("""<div class="entryindent">\n""")
        return True

    def print_head(self, entry, prop):
        prefix_content = f"""<span onclick='toggle_element(this);'>{prop}:</span> """
        if prop is None:
            prefix_content = ""
        head = print_head(entry, prefix_content=prefix_content, print_label=True)
        return head

    def close_sections(self, level=0):
        diff = self.recent_depth + 1 - level
        self.content_list.append("</div>\n" * diff)
        self.recent_depth = level


def print_head(entry, prefix_content="", postfix_content="", print_label=False):
    if not isinstance(entry, Entry):
        entry_value = escape_html(entry)
        return f"""<div class="entryhead">{prefix_content}{entry_value}{postfix_content}</div>\n"""
    label_content = ""
    if print_label:
        label_content = " " + get_entry_name(entry)
    return (
        f"""<div class="entryhead">{prefix_content}{entry.get_type()} {get_entry_id_href(entry)}"""
        f"""{label_content}{postfix_content}</div>\n"""
    )


def get_entry_id_href(entry: Entry):
    entry_id = entry.get_id()
    return f"""<a href="{entry_id}.html">{entry_id}</a>"""


def escape_html(content: str) -> str:
    return html.escape(content)
