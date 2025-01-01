#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
)
from gcclangrawparser.langanalyze import (
    StructAnalyzer,
    get_decl_namespace_list,
    get_function_args,
    get_function_ret,
    get_number_entry_value,
)
from gcclangrawparser.diagram.activitydiagram import (
    ActivityDiagramGenerator,
    FuncData,
    FunctionArg,
    FuncStatement,
    FuncStatType,
)


_LOGGER = logging.getLogger(__name__)


def generate_control_flow_graph(content: LangContent, out_path, include_internals=False):
    _LOGGER.info("generating memory layout graph to %s", out_path)
    parent_dir = os.path.abspath(os.path.join(out_path, os.pardir))
    os.makedirs(parent_dir, exist_ok=True)

    content.convert_entries()

    graph_data = ControlFlowData(content, include_internals)
    graph_info = graph_data.generate_data()

    diagram_gen = ActivityDiagramGenerator(graph_info)
    diagram_gen.generate(out_path)

    _LOGGER.info("generating completed")


class ControlFlowData:

    def __init__(self, content, include_internals=False):
        self.content = content
        self.include_internals = include_internals
        self.analyzer = StructAnalyzer(content, include_internals)

    def generate_data(self):
        ret_dict = {}
        dcls_list = self.content.get_entries("dcls")
        for dcls_entry in dcls_list:
            info_list = self.get_function_info(dcls_entry)
            if info_list:
                func_names = [item.name for item in info_list]
                _LOGGER.info("found items %s for entry %s", func_names, dcls_entry.get_id())
                for info in info_list:
                    ret_dict[info.name] = info
        return ret_dict

    def get_function_info(self, dcls_entry: Entry):
        if dcls_entry.get_type() != "function_decl":
            return None
        if is_entry_language_internal(dcls_entry):
            return None

        ret_list = []

        func_name = get_decl_namespace_list(dcls_entry)
        func_name = "::".join(func_name)

        func_data = FuncData(func_name)

        args_data = get_function_args(dcls_entry)
        args_list = []
        for arg_item in args_data:
            arg_name, arg_type = arg_item
            args_list.append(FunctionArg(arg_name, arg_type))
        func_data.args = args_list

        func_type_entry = dcls_entry.get("type")
        func_data.returntype = get_function_ret(func_type_entry)

        func_body = dcls_entry.get("body")
        func_data.statements = handle_func_body(func_body)
        ret_list.append(func_data)
        return ret_list


def handle_func_body(statement_entry: Entry) -> List[FuncStatement]:
    analyzer = ScopeAnalysis()
    return analyzer.analyze(statement_entry)


class ScopeAnalysis:

    def __init__(self):
        self.vars = []
        self.decl_expr_counter = -1

    def analyze(self, statement_entry: Entry):
        type_name = statement_entry.get_type()
        if type_name != "bind_expr":
            stat_list: List[FuncStatement] = []
            self._analyze_func(statement_entry, stat_list)
            return stat_list

        # new scope
        self._read_var_defs(statement_entry)
        body_entry = statement_entry.get("body")
        stat_list: List[FuncStatement] = []
        self._analyze_func(body_entry, stat_list)
        return stat_list

    def _read_var_defs(self, bind_expr: Entry):
        bind_vars = bind_expr.get_sub_entries("vars")
        for _var_prop, var_item in bind_vars:
            type_name = var_item.get_type()
            if type_name != "var_decl":
                raise RuntimeError("invalid type")
            init_entry = var_item.get("init")
            if not init_entry:
                self.vars.append(None)
                continue
            var_name = get_entry_name(var_item)
            init_expr = self._analyze_func(init_entry, [])
            decl_expr = f"{var_name} = {init_expr}"
            self.vars.append(decl_expr)

    def _analyze_func(self, statement_entry: Entry, stat_list: List[FuncStatement]) -> str:
        type_name = statement_entry.get_type()

        if type_name == "bind_expr":
            # new scope
            scope_analysis = ScopeAnalysis()
            bind_list = scope_analysis.analyze(statement_entry)
            stat_list.extend(bind_list)
            return

        if type_name == "statement_list":
            index_entries = get_index_entries(statement_entry)
            for index_item in index_entries:
                self._analyze_func(index_item, stat_list)
            return

        if type_name == "decl_expr":
            self.decl_expr_counter += 1
            decl_expr = self.vars[self.decl_expr_counter]
            if decl_expr:
                decl_node = FuncStatement(decl_expr, FuncStatType.NODE)
                stat_list.append(decl_node)
            return

        if type_name == "var_decl":
            return get_entry_name(statement_entry)

        if type_name == "function_decl":
            note = statement_entry.get("note")
            if note == "artificial":
                ## skip artificial elements
                return
            func_name = get_decl_namespace_list(statement_entry)
            func_name = "::".join(func_name)
            return func_name

        if type_name == "parm_decl":
            return get_entry_name(statement_entry)

        if type_name == "cond_expr":
            # if expression
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            if_node = FuncStatement(op0_expr, FuncStatType.IF)

            true_stats: List[FuncStatement] = []
            op1_entry = statement_entry.get("op 1")  ## true branch
            self._analyze_func(op1_entry, true_stats)
            if_node.items.append(true_stats)

            false_stats: List[FuncStatement] = []
            op2_entry = statement_entry.get("op 2")  ## false branch
            self._analyze_func(op2_entry, false_stats)
            if_node.items.append(false_stats)

            stat_list.append(if_node)
            return

        if type_name == "eq_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} == {op1_expr}"

        if type_name == "bit_and_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} & {op1_expr}"

        if type_name == "trunc_mod_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} % {op1_expr}"

        if type_name == "switch_expr":
            self._analyze_switch(statement_entry, stat_list)
            return

        if type_name == "return_expr":
            if self._find_return_item(stat_list) > -1:
                _LOGGER.error("return node already added to the list")
                return
            expr_entry = statement_entry.get("expr")
            expr_expr = self._analyze_func(expr_entry, stat_list)
            ret_expr = f"return {expr_expr}"
            stat_list.append(FuncStatement(ret_expr, FuncStatType.STOP))
            return

        if type_name == "nop_expr":
            op_entry = statement_entry.get("op 0")
            return self._analyze_func(op_entry, stat_list)

        if type_name == "cleanup_point_expr":
            op_entry = statement_entry.get("op 0")
            self._analyze_func(op_entry, stat_list)
            return

        if type_name == "expr_stmt":
            expr_entry = statement_entry.get("expr")
            expr = self._analyze_func(expr_entry, stat_list)
            if expr is None:
                raise RuntimeError(f"invalid case for entry {expr_entry.get_id()}")
            stat_list.append(FuncStatement(expr, FuncStatType.NODE))
            return

        if type_name == "call_expr":
            params_list = []
            arg_entries = get_index_entries(statement_entry)
            for arg_item in arg_entries:
                arg_expr = self._analyze_func(arg_item, stat_list)
                params_list.append(arg_expr)
            params_str = ", ".join(params_list)
            expr_entry = statement_entry.get("fn")
            call_expr = self._analyze_func(expr_entry, stat_list)
            # TODO: handle passing parameters
            return f"{call_expr}({params_str})"

        if type_name == "init_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            if op0_expr is None:
                return op1_expr
            return f"{op0_expr} = {op1_expr}"

        if type_name == "modify_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} = {op1_expr}"

        if type_name == "convert_expr":
            expr_entry = statement_entry.get("op 0")
            return self._analyze_func(expr_entry, stat_list)

        if type_name == "addr_expr":
            expr_entry = statement_entry.get("op 0")
            return self._analyze_func(expr_entry, stat_list)

        if type_name == "plus_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} + {op1_expr}"

        if type_name == "mult_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr} * {op1_expr}"

        if type_name == "result_decl":
            return

        if type_name == "integer_cst":
            return get_entry_name(statement_entry)

        _LOGGER.error("unhandled statement type %s", type_name)

        node = FuncStatement(f"== unhandled statement {statement_entry.get_id()} ==", FuncStatType.NODE)
        node.color = "#orange"
        stat_list.append(node)
        return

    def _analyze_switch(self, statement_entry: Entry, stat_list: List[FuncStatement]):
        switch_node = FuncStatement("", FuncStatType.SWITCH)

        cond_entry = statement_entry.get("cond")
        cond_expr = self._analyze_func(cond_entry, [])
        switch_node.name = cond_expr

        body_entry = statement_entry.get("body")
        subbody_entry = body_entry.get("0")
        if subbody_entry.get_type() == "bind_expr":
            body_entry = subbody_entry.get("body")

        index_entries = get_index_entries(body_entry)
        # entries_num = len(index_entries)
        # if entries_num % 2 != 0:
        #     raise RuntimeError(f"invalid number of operations in switch entry {statement_entry.get_id()}")
        #
        # for index in range(0, entries_num, 2):

        recent_case_value = None  # list of one element
        recent_case_fallthrough = True  # bool
        recent_case_stats: List[FuncStatement] = None

        for case_entry in index_entries:
            case_entry_type = case_entry.get_type()
            if case_entry_type == "case_label_expr":
                if recent_case_value is not None:
                    ## fallthrough case
                    case_value = recent_case_value[0]
                    case_data = self._get_switch_case(case_value, recent_case_fallthrough, recent_case_stats)
                    if case_data:
                        switch_node.items.append(case_data)
                        recent_case_value = None
                        recent_case_fallthrough = True  ## can happen two case_label_expr in row
                        recent_case_stats = None

                case_value_entry = case_entry.get("low")
                if case_value_entry is not None:
                    ## normal case
                    recent_case_value = [get_number_entry_value(case_value_entry)]
                else:
                    ## default case
                    recent_case_value = [None]
                continue

            if case_entry_type in ("return_expr"):
                if recent_case_value is None:
                    raise RuntimeError("invalid switch case data")
                recent_case_fallthrough = False
                recent_case_stats = []
                self._analyze_func(case_entry, recent_case_stats)
                continue

            if case_entry_type in ("bind_expr"):
                if recent_case_value is None:
                    raise RuntimeError("invalid switch case data")
                recent_case_fallthrough = False
                recent_case_stats = []
                self._analyze_func(case_entry, recent_case_stats)
                continue

            if case_entry_type in ("cleanup_point_expr"):
                if recent_case_value is None:
                    raise RuntimeError("invalid switch case data")
                recent_case_fallthrough = True
                recent_case_stats = []
                self._analyze_func(case_entry, recent_case_stats)
                continue

            if case_entry_type == "goto_expr":
                recent_case_fallthrough = False
                continue

            raise RuntimeError(f"unhandled switch case type: {case_entry_type}")

            # expr_entry = index_entries[index + 1]
            # case_stats = []
            # self._analyze_func(expr_entry, case_stats)
            # switch_node.items.append( (case_value, case_stats) )

        if recent_case_value is None:
            raise RuntimeError("invalid switch case data")
        case_value = recent_case_value[0]
        case_data = self._get_switch_case(case_value, recent_case_fallthrough, recent_case_stats)
        if case_data:
            switch_node.items.append(case_data)
            recent_case_value = None
            recent_case_fallthrough = None
            recent_case_stats = None

        stat_list.append(switch_node)

    def _get_switch_case(self, case_value, is_fallthrough, case_statements):
        if case_statements is None:
            case_statements = []
        return (case_value, is_fallthrough, case_statements)

    def _find_return_item(self, statements_list):
        for index, item in enumerate(statements_list):
            if item.type == FuncStatType.STOP:
                return index
        return -1


def get_index_entries(entry: Entry):
    ret_list = []
    statement_index = 0
    while True:
        statement_str = f"{statement_index}"
        statement_index += 1
        statement_value_entry = entry.get(statement_str)
        if statement_value_entry is None:
            break
        ret_list.append(statement_value_entry)
    return ret_list
