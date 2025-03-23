#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Any, Dict

from gccuml.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_function_full_name,
    get_function_args,
    get_function_ret,
)
from gccuml.langanalyze import (
    StructAnalyzer,
)
from gccuml.diagram.activitydata import (
    LabeledCard,
    FunctionArg,
)
from gccuml.diagram.activitydiagram import generate_diagram
from gccuml.langparser import parse_raw
from gccuml.configyaml import Filter
from gccuml.expressionanalyze import ScopeAnalysis


_LOGGER = logging.getLogger(__name__)


def generate_control_flow_graph_config(config: Dict[Any, Any]):
    input_files = config.get("inputfiles")
    if not input_files:
        raise RuntimeError("no input files given")
    if len(input_files) > 1:
        raise RuntimeError(f"multiple input files not supported: {input_files}")
    raw_file_path = input_files[0]
    _LOGGER.info("parsing input file %s", raw_file_path)
    reduce_paths = config.get("reducepaths", False)
    content: LangContent = parse_raw(raw_file_path, reduce_paths)
    if content is None:
        raise RuntimeError(f"unable to parse {raw_file_path}")
    out_path = config.get("outpath")
    if not out_path:
        raise RuntimeError("no output path given")
    include_internals = config.get("includeinternals", False)
    item_filter: Filter = Filter.create(config)
    generate_control_flow_graph(
        content, out_path, include_internals=include_internals, engine=config["engine"], item_filter=item_filter
    )


def get_engine_file_extension(diagram_engine):
    if diagram_engine == "dot":
        return "dot"
    if diagram_engine == "plantuml":
        return "puml"
    return "dot"


def generate_control_flow_graph(
    content: LangContent, out_path, include_internals=False, engine="dot", item_filter: Filter = None
):
    _LOGGER.info("generating control flow graph to %s", out_path)
    if item_filter is None:
        item_filter = Filter()
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_entries()

    graph_data = ControlFlowData(content, include_internals)
    graph_info = graph_data.generate_data()

    generate_diagram(engine, graph_info, out_path)

    _LOGGER.info("generating completed")


class ControlFlowData:

    def __init__(self, content: LangContent, include_internals=False):
        self.content = content
        self.include_internals = include_internals
        self.analyzer = StructAnalyzer(content, include_internals)

    def generate_data(self):
        ret_dict = {}

        all_entries = self.content.get_entries_all()
        for entry in all_entries:
            info_list: List[LabeledCard] = self.get_function_info(entry)
            if info_list:
                func_names = [item.label for item in info_list]
                _LOGGER.info("found items %s for entry %s", func_names, entry.get_id())
                for info in info_list:
                    ret_dict[info.label] = info

        # dcls_list = self.content.get_entries("dcls")
        # for dcls_entry in dcls_list:
        #     info_list: List[LabeledCard] = self.get_function_info(dcls_entry)
        #     if info_list:
        #         func_names = [item.label for item in info_list]
        #         _LOGGER.info("found items %s for entry %s", func_names, dcls_entry.get_id())
        #         for info in info_list:
        #             ret_dict[info.label] = info
        #
        # flds_list = self.content.get_entries("flds")
        # for flds_entry in flds_list:
        #     info_list: List[LabeledCard] = self.get_function_info(flds_entry)
        #     if info_list:
        #         func_names = [item.label for item in info_list]
        #         _LOGGER.info("found items %s for entry %s", func_names, flds_entry.get_id())
        #         for info in info_list:
        #             ret_dict[info.label] = info

        return ret_dict

    def get_function_info(self, dcls_entry: Entry) -> List[LabeledCard]:
        if dcls_entry.get_type() != "function_decl":
            return None
        if is_entry_language_internal(dcls_entry):
            return None

        note_entry = dcls_entry.get("note")
        if note_entry:
            if "pseudo tmpl" in note_entry:
                return None

        ret_list = []

        func_name = get_function_full_name(dcls_entry)

        args_data = get_function_args(dcls_entry)
        args_list = []
        for arg_item in args_data:
            arg_name, arg_type = arg_item
            args_list.append(FunctionArg(arg_name, arg_type))

        func_type_entry = dcls_entry.get("type")
        func_returntype = get_function_ret(func_type_entry)

        func_body_list = dcls_entry.get_list("body")
        if func_body_list and "undefined" in func_body_list:
            func_body_list.remove("undefined")
        if not func_body_list:
            ## no body
            return []
        if len(func_body_list) > 1:
            raise RuntimeError(f"multiple bodies not supported for entry {repr(dcls_entry)}")
        func_body = func_body_list[0]
        analyzer = ScopeAnalysis(self.content)
        statements = analyzer.analyze(func_body)

        if func_name == "::main" and statements:
            ## remove last element - it's repeated "return" statement
            del statements[-1]

        # TODO: resolve
        # if statements is not None:
        #     if statements:
        #         last_item = statements[-1]
        #         if last_item.type != StatementType.STOP:
        #             ## probably return void function - add stop node
        #             stop_node = TypedStatement("", StatementType.STOP)
        #             statements.append(stop_node)
        #     else:
        #         ## probably return void function - add stop node
        #         stop_node = TypedStatement("", StatementType.STOP)
        #         statements.append(stop_node)

        # ctor = is_ctor(dcls_entry)
        # if ctor:
        #     # constructors and destructors does not have return statement - add stop node
        #     decl_node = TypedStatement("", StatementType.STOP)
        #     statements.append(decl_node)

        func_data = LabeledCard()
        func_data.set_label(func_name, args_list, func_returntype)
        func_data.subitems = statements
        func_data.has_return = True
        ret_list.append(func_data)
        return ret_list


def is_ctor(function_decl: Entry) -> bool:
    method_note_list = function_decl.get_list("note")
    if not method_note_list:
        return False
    if "constructor" in method_note_list:
        return True
    if "destructor" in method_note_list:
        return True
    return False
