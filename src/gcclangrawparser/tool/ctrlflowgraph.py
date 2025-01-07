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

from gcclangrawparser.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
    get_number_entry_value,
    get_decl_namespace_list,
    get_type_name_mod,
    get_entry_repr,
)
from gcclangrawparser.langanalyze import (
    StructAnalyzer,
    get_function_args,
    get_function_ret,
    is_method_of_instance,
    get_function_full_name,
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

        flds_list = self.content.get_entries("flds")
        for flds_entry in flds_list:
            info_list = self.get_function_info(flds_entry)
            if info_list:
                func_names = [item.name for item in info_list]
                _LOGGER.info("found items %s for entry %s", func_names, flds_entry.get_id())
                for info in info_list:
                    ret_dict[info.name] = info

        return ret_dict

    def get_function_info(self, dcls_entry: Entry):
        if dcls_entry.get_type() != "function_decl":
            return None
        if is_entry_language_internal(dcls_entry):
            return None

        ret_list = []

        func_name = get_function_full_name(dcls_entry)

        args_data = get_function_args(dcls_entry)
        args_list = []
        for arg_item in args_data:
            arg_name, arg_type = arg_item
            args_list.append(FunctionArg(arg_name, arg_type))

        func_data = FuncData(func_name)
        func_data.args = args_list

        func_type_entry = dcls_entry.get("type")
        func_data.returntype = get_function_ret(func_type_entry)

        func_body_list = dcls_entry.get_list("body")
        if func_body_list and "undefined" in func_body_list:
            func_body_list.remove("undefined")
        if not func_body_list:
            ## no body
            return []
        if len(func_body_list) > 1:
            raise RuntimeError(f"multiple bodies not supported for entry {repr(dcls_entry)}")
        func_body = func_body_list[0]
        analyzer = ScopeAnalysis()
        func_data.statements = analyzer.analyze(func_body)

        ctor = is_ctor(dcls_entry)
        if ctor:
            # constructors and destructors does not have return statement - add stop node
            decl_node = FuncStatement("", FuncStatType.STOP)
            func_data.statements.append(decl_node)

        ret_list.append(func_data)
        return ret_list


OP1_SET = {"cleanup_point_expr", "convert_expr", "fix_trunc_expr", "float_expr", "non_lvalue_expr", "nop_expr"}


OP2_DICT = {
    "eq_expr": "==",
    "bit_and_expr": "&",
    "trunc_mod_expr": "%",
    "modify_expr": "=",
    "plus_expr": "+",
    "pointer_plus_expr": "+",
    "minus_expr": "-",
    "mult_expr": "*",
    "rdiv_expr": "/",
    "trunc_div_expr": "/",
}


class ScopeAnalysis:

    def __init__(self):
        self.vars = []
        self.var_defs: Dict[str, Any] = {}
        self.scope_vars = set()
        self.decl_expr_counter = -1

    def analyze(self, statement_entry: Entry):
        stat_list: List[FuncStatement] = []
        type_name = statement_entry.get_type()
        if type_name != "bind_expr":
            self._analyze_func(statement_entry, stat_list)
            return stat_list

        # new scope
        self._read_var_defs(statement_entry)
        body_entry = statement_entry.get("body")
        self._analyze_func(body_entry, stat_list)
        return stat_list

    def _read_var_defs(self, bind_expr: Entry):
        bind_vars = bind_expr.get_sub_entries("vars")
        for _var_prop, var_item in bind_vars:
            var_name = get_entry_name(var_item)
            decl_expr = self._handle_var(var_item, [])
            self.vars.append((var_name, decl_expr))

    def _handle_var(self, var_decl: Entry, stat_list: List[FuncStatement]):
        var_name = get_entry_name(var_decl)
        var_type = var_decl.get("type")
        var_type_name, var_type_mod = get_type_name_mod(var_type)
        type_label = var_type_name
        if var_type_mod is not None:
            type_label = f"{var_type_mod} {var_type_name}"

        init_entry = var_decl.get("init")
        if not init_entry:
            decl_expr = f"{type_label} {var_name};"
            return decl_expr
        init_expr = self._analyze_func(init_entry, stat_list)
        decl_expr = f"{type_label} {var_name} = {init_expr}"
        return decl_expr

    def _analyze_func(self, statement_entry: Entry, stat_list: List[FuncStatement]) -> str:
        op2_exp: str = self._handle_op2(statement_entry, stat_list)
        if op2_exp is not None:
            return op2_exp

        num_val = get_number_entry_value(statement_entry, fail_exception=False)
        if num_val is not None:
            return num_val

        type_name = statement_entry.get_type()

        if type_name in OP1_SET:
            op_entry = statement_entry.get("op 0")
            return self._analyze_func(op_entry, stat_list)

        if type_name in ("field_decl"):
            return get_entry_repr(statement_entry)
        if type_name in ("parm_decl"):
            return get_entry_name(statement_entry)
        if type_name in ("var_decl"):
            var_name = get_entry_name(statement_entry)
            # if var_name not in self.scope_vars:
            #     self.scope_vars.add(var_name)
            #     var_expr = self._handle_var(statement_entry, stat_list)
            #     var_node = FuncStatement(var_expr, FuncStatType.NODE)
            #     stat_list.append(var_node)
            return var_name

        if type_name == "decl_expr":
            self.decl_expr_counter += 1
            var_name, decl_expr = self.vars[self.decl_expr_counter]
            if decl_expr:
                decl_node = FuncStatement(decl_expr, FuncStatType.NODE)
                stat_list.append(decl_node)
            self.scope_vars.add(var_name)
            return None

        if type_name == "component_ref":
            op1_entry = statement_entry.get("op 1")
            member_name = get_entry_name(op1_entry, None)
            if member_name:
                return member_name
            ## access to unnamed member (base class)
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry, stat_list)

        if type_name == "indirect_ref":
            op_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op_entry, stat_list)
            return f"(*{op0_expr})"

        if type_name == "addr_expr":
            op_entry = statement_entry.get("op 0")
            item_expr = self._analyze_func(op_entry, stat_list)
            return "(&" + item_expr + ")"

        if type_name == "array_ref":
            op0_entry = statement_entry.get("op 0")  ## element
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")  ## index
            op1_expr = self._analyze_func(op1_entry, stat_list)
            return f"{op0_expr}[{op1_expr}]"

        if type_name == "cond_expr":
            self._handle_if(statement_entry, stat_list)
            return None

        if type_name == "switch_expr":
            self._handle_switch(statement_entry, stat_list)
            return None

        if type_name == "bind_expr":
            # new scope
            scope_analysis = ScopeAnalysis()
            bind_list = scope_analysis.analyze(statement_entry)
            stat_list.extend(bind_list)
            return None

        if type_name == "statement_list":
            index_entries = get_index_entries(statement_entry)
            for index_item in index_entries:
                self._analyze_func(index_item, stat_list)
            return None

        if type_name == "function_decl":
            note_list = statement_entry.get_list("note")
            if "artificial" in note_list:
                ## skip artificial elements
                return None
            func_name = get_decl_namespace_list(statement_entry)
            func_name = "::".join(func_name)
            return func_name

        if type_name == "return_expr":
            if self._find_return_item(stat_list) > -1:
                _LOGGER.error("return node already added to the list")
                return None
            expr_entry = statement_entry.get("expr")
            expr_expr = self._analyze_func(expr_entry, stat_list)
            ret_expr = f"return {expr_expr}"
            stat_list.append(FuncStatement(ret_expr, FuncStatType.STOP))
            return None

        if type_name == "expr_stmt":
            expr_entry = statement_entry.get("expr")
            expr = self._analyze_func(expr_entry, stat_list)
            if expr is not None:
                ## happens when "[[fallthrough]];" is used explicit
                stat_list.append(FuncStatement(expr, FuncStatType.NODE))
            return None

        if type_name == "call_expr":
            return self._handle_call(statement_entry, stat_list)

        # if type_name == "compound_expr":
        #     op0_entry = statement_entry.get("op 0")
        #     op0_expr = self._analyze_func(op0_entry, stat_list)
        #     op1_entry = statement_entry.get("op 1")
        #     op1_expr = self._analyze_func(op1_entry, stat_list)
        #     return f"{op0_expr}{op1_expr}"
        #
        # if type_name == "target_expr":
        #     decl_entry = statement_entry.get("decl")
        #     decl_expr = self._analyze_func(decl_entry, stat_list)
        #     init_entry = statement_entry.get("init")
        #     init_expr = self._analyze_func(init_entry, stat_list)
        #     return f"{decl_expr}{init_expr}"

        if type_name == "init_expr":
            op0_entry = statement_entry.get("op 0")
            op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")
            op1_expr = self._analyze_func(op1_entry, stat_list)
            if op0_expr is None:
                return op1_expr
            return f"{op0_expr} = {op1_expr}"

        if type_name == "constructor":
            # array and object initialization
            init_list = []
            items_num = int(statement_entry.get("lngt"))
            data_list = statement_entry.get_ordered_tuples(["idx", "val"])
            if len(data_list) != items_num:
                raise RuntimeError("invalid number of values in entry: {statement_entry}")
            for data_item in data_list:
                data_idx = data_item[0]
                data_val = data_item[1]
                idx_expr = self._analyze_func(data_idx, stat_list)
                val_expr = self._analyze_func(data_val, stat_list)
                item_expr = f"[{idx_expr}] = {val_expr}"
                init_list.append(item_expr)
            whole_expr = ", ".join(init_list)
            return f"{{{whole_expr}}}"

        if type_name == "result_decl":
            ## do nothing
            return None

        _LOGGER.error("unhandled statement type %s %s", statement_entry.get_id(), type_name)

        node = FuncStatement(f"== unhandled statement {statement_entry.get_id()} ==", FuncStatType.NODE)
        node.color = "#orange"
        stat_list.append(node)
        return None

    def _handle_op2(self, statement_entry: Entry, stat_list: List[FuncStatement]) -> str:
        if statement_entry is None:
            pass
        type_name = statement_entry.get_type()
        op_sign = OP2_DICT.get(type_name)
        if op_sign is None:
            return None
        op0_entry = statement_entry.get("op 0")
        op0_expr = self._analyze_func(op0_entry, stat_list)
        op1_entry = statement_entry.get("op 1")
        op1_expr = self._analyze_func(op1_entry, stat_list)
        return f"{op0_expr} {op_sign} {op1_expr}"

    def _handle_call(self, statement_entry: Entry, stat_list: List[FuncStatement]):
        expr_entry = statement_entry.get("fn")
        if expr_entry is None:
            ## happens when "[[fallthrough]];" is used explicit
            return None
        func_decl = expr_entry.get("op 0")
        if func_decl is None:
            # only known method declaration (unknown method)
            return None
        is_meth = is_method_of_instance(func_decl)
        func_name = ""
        if is_meth:
            func_name = get_entry_name(func_decl)
        else:
            func_name = get_entry_repr(func_decl)
        params_list = []
        arg_entries = get_index_entries(statement_entry)
        for arg_item in arg_entries:
            arg_expr = self._analyze_func(arg_item, stat_list)
            params_list.append(arg_expr)
        obj_name = ""
        if is_meth:
            # in case of method first parameter is object
            first_param = params_list.pop(0)
            obj_name = f"{first_param}->"
        params_str = ", ".join(params_list)
        return f"{obj_name}{func_name}({params_str})"

    def _handle_if(self, statement_entry: Entry, stat_list: List[FuncStatement]):
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

    def _handle_switch(self, statement_entry: Entry, stat_list: List[FuncStatement]):
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


def is_ctor(function_decl: Entry) -> bool:
    method_note_list = function_decl.get_list("note")
    if not method_note_list:
        return False
    if "constructor" in method_note_list:
        return True
    if "destructor" in method_note_list:
        return True
    return False
