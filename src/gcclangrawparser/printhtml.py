#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import io
from typing import Dict, Any, List

import multiprocessing
from multiprocessing import Pool

# from multiprocessing.pool import ThreadPool as Pool

from showgraph.graphviz import Graph, set_node_style

from gcclangrawparser.langparser import LangContent, Entry, get_entry_name
from gcclangrawparser.io import write_file


def print_html(content: LangContent, out_dir):
    print("writing HTML output")
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

    # for entry in content.content_objs.values():
    #     generate_entry_page( entry, depends_dict, out_dir )

    proc_num = multiprocessing.cpu_count()
    with Pool(proc_num) as process_pool:
        # with Pool(processes=1) as process_pool:
        result_queue = []

        entries_list = list(content.content_objs.values())
        ch_size = int(len(entries_list) / proc_num) + 1
        chunks = [entries_list[x : x + ch_size] for x in range(0, len(entries_list), ch_size)]

        for sublist in chunks:
            async_result = process_pool.apply_async(generate_pages, [sublist, depends_dict, out_dir])
            result_queue.append(async_result)

        for async_result in result_queue:
            async_result.get()

    print("writing completed")


def generate_pages(entries, depends_dict, out_dir):
    for entry in entries:
        generate_entry_page(entry, depends_dict, out_dir)


def generate_entry_page(entry, depends_dict, out_dir):
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

    # TODO: operation takes very long - optimize it
    img_content = get_graph_as_format(graph, "svg")

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
    </style>
</head>
<body>
    <div class="section"><a href="@1.html">back to @1</a></div>
    <div class="graphsection section">
{img_content}
    </div>
</body>
</html>
"""

    out_file = os.path.join(out_dir, f"{entry.get_id()}.html")
    write_file(out_file, content)


def get_entry_label(entry):
    if entry.get_type() == "identifier_node":
        return get_entry_name(entry)
    if entry.get_type() == "translation_unit_decl":
        return get_entry_name(entry)
    if entry.get_type() == "namespace_decl":
        return get_entry_name(entry)
    if entry.get_type() == "function_decl":
        return get_entry_name(entry)
    return None


# png, svg, cmapx
def get_graph_as_format(graph: Graph, data_format):
    with io.BytesIO() as buffer:
        graph.write(buffer, file_format=data_format)
        contents = buffer.getvalue()
        contents_str = contents.decode("utf-8")
        return contents_str
