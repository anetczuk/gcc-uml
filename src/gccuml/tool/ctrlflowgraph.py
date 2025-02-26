#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import List, Any, Dict, Tuple, Set

from gccuml.langcontent import (
    LangContent,
    Entry,
    is_entry_language_internal,
    get_entry_name,
    get_number_entry_value,
    get_decl_namespace_list,
)
from gccuml.langanalyze import (
    StructAnalyzer,
    get_function_args,
    get_function_ret,
    is_method_of_instance,
    get_function_full_name,
    find_class_vtable_var_decl,
    get_type_name_mod,
    get_entry_repr,
    is_entry_code_class,
)
from gccuml.diagram.activitydata import (
    LabeledCard,
    FunctionArg,
    Statement,
    StatementType,
    LabeledGroup,
    StatementList,
    SwitchStatement,
    TypedStatement,
)
from gccuml.diagram.activitydiagram import generate_diagram


_LOGGER = logging.getLogger(__name__)


COLOR_NODE_NOTICE = "orange"


def generate_control_flow_graph(content: LangContent, out_path, include_internals=False, engine="dot"):
    _LOGGER.info("generating control flow graph to %s", out_path)
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


## tcc_expression
UNSUPPORTED_EXPRESSION_SET = {
    "truth_and_expr",
    "target_expr",
    "ctor_initializer",
    "modop_expr",
    "sizeof_expr",
    "vec_perm_expr",
    "annotate_expr",
    "vec_cond_expr",
    "va_arg_expr",
    "empty_class_expr",
    "expr_pack_expansion",
    "alignof_expr",
    "nw_expr",
    "dl_expr",
    "tag_defn",
    "addressof_expr",
}


EXPR_UNSUPPORTED_SET = {
    "cast_expr",
    "template_id_expr",
    "component_ref",
    "compound_expr",
    "overload",
    "function_decl",
    "baselink",
    "scope_ref",
    "nop_expr",
    "non_lvalue_expr",
    "parm_decl",
    "array_ref",
    "indirect_ref",
    "cond_expr",
    "call_expr",
    "pointer_plus_expr",
    "convert_expr",
    "dotstar_expr",
    "member_ref",
    "constructor",
}


## elements of type tcc_unary
OP_UNARY_DICT = {
    "convert_expr": (None, None),
    "nop_expr": (None, None),
    "non_lvalue_expr": (None, None),
    "float_expr": (None, None),
    "fix_trunc_expr": (None, None),
    "paren_expr": (None, None),
    "negate_expr": ("-", None),
    "bit_not_expr": ("~", None),
    "abs_expr": ("|", "|"),
    "absu_expr": ("|", "|"),
    "conj_expr": ("_CONJ_(", ")"),
    ### still unhandled
    # vec_duplicate_expr
    # fix_trunc_expr
    # float_expr
    # convert_expr
    # addr_space_convert_expr
    # fixed_convert_expr
    # nop_expr
    # vec_unpack_hi_expr
    # vec_unpack_lo_expr
    # vec_unpack_float_hi_expr
    # vec_unpack_float_lo_expr
    # vec_unpack_fix_trunc_hi_expr
    # vec_unpack_fix_trunc_lo_expr
    # implicit_conv_expr
    # noexcept_expr
    # unary_plus_expr
}


## cast elements of type tcc_unary
OP_UNARY_CAST_DICT = {
    "cast_expr": (None,),
    "static_cast_expr": ("_STATIC_CAST_",),
    "const_cast_expr": ("_CONST_CAST_",),
    "dynamic_cast_expr": ("_DYNAMIC_CAST_",),
    "reinterpret_cast_expr": ("_REINTERPRET_CAST_",),
}


## elements of type tcc_binary
OP_BINARY_DICT = {
    "bit_and_expr": (None, "&", None),
    "bit_ior_expr": (None, "|", None),
    "bit_xor_expr": (None, "^", None),
    "trunc_mod_expr": (None, "%", None),
    "plus_expr": (None, "+", None),
    "minus_expr": (None, "-", None),
    "pointer_plus_expr": (None, "+", None),
    "pointer_diff_expr": (None, "-", None),
    "mult_expr": (None, "*", None),
    "rdiv_expr": (None, "/", None),
    "trunc_div_expr": (None, "/", None),
    "exact_div_expr": (None, "/", None),
    "lshift_expr": (None, "<<", None),
    "rshift_expr": (None, ">>", None),
    "lrotate_expr": (None, "<<", None),
    "rrotate_expr": (None, ">>", None),
    "max_expr": ("_MAX_(", ",", ")"),
    "min_expr": ("_MIN_(", ",", ")"),
    "complex_expr": ("_COMPLEX_(", ",", ")"),
}


## elements of type tcc_comparison
OP_COMPARISON_DICT = {
    "eq_expr": (None, "==", None),
    "ne_expr": (None, "!=", None),
    "lt_expr": (None, "<", None),
    "le_expr": (None, "<=", None),
    "gt_expr": (None, ">", None),
    "ge_expr": (None, ">=", None),
    "uneq_expr": (None, "==", None),
    "unlt_expr": (None, "<", None),
    "unle_expr": (None, "<=", None),
    "ungt_expr": (None, ">", None),
    "unge_expr": (None, ">=", None),
    "ordered_expr": ("_ORDERED_(", ",", ")"),
    "unordered_expr": ("_UNORDERED_(", ",", ")"),
}


## some elements of type tcc_expression
OP1_EXPR_DICT = {
    "preincrement_expr": ("++", None),
    "predecrement_expr": ("--", None),
    "postincrement_expr": (None, "++"),
    "postdecrement_expr": (None, "--"),
    "truth_not_expr": ("!", None),
}


## some elements of type tcc_expression
OP2_EXPR_DICT = {
    "truth_andif_expr": (None, "&&", None),
    "truth_orif_expr": (None, "||", None),
    "truth_or_expr": (None, "||", None),
    "modify_expr": (None, "=", None),
}


class ScopeAnalysis:

    def __init__(self, content: LangContent):
        self.content = content
        self.vars: List[Tuple[str, str]] = []
        self.var_defs: Dict[str, Any] = {}
        self.scope_vars: Set[str] = set()
        self.decl_expr_counter = -1

    def analyze(self, statement_entry: Entry):
        stat_list: List[Statement] = []
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

    def _handle_var(self, var_decl: Entry, stat_list: List[Statement]):
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
        _valid, init_expr = self._analyze_func(init_entry, stat_list)
        decl_expr = f"{type_label} {var_name} = {init_expr}"
        return decl_expr

    def _analyze_func(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        if statement_entry is None:
            return (False, None)

        ## tcc_constant
        stat_valid, stat_name = self._handle_const(statement_entry)
        if stat_valid:
            return (True, stat_name)

        ## tcc_unary
        valid_op1, op1_exp = self._handle_unary(statement_entry, stat_list)
        if valid_op1:
            return (True, op1_exp)

        ## tcc_binary
        stat_valid, stat_name = self._handle_binary(statement_entry, stat_list)
        if stat_valid:
            return (True, stat_name)

        ## tcc_comparison
        valid_op1, op1_exp = self._handle_comparison(statement_entry, stat_list)
        if valid_op1:
            return (True, op1_exp)

        ## tcc_statement
        other_valid_expr, other_name_exp = self._handle_statement(statement_entry, stat_list)
        if other_valid_expr:
            return (True, other_name_exp)

        ## tcc_expression
        other_valid_expr, other_name_exp = self._handle_expression(statement_entry, stat_list)
        if other_valid_expr:
            return (True, other_name_exp)

        type_name = statement_entry.get_type()

        ## tcc_reference
        if type_name in (
            "bit_field_ref",
            "realpart_expr",
            "imagpart_expr",
            "scope_ref",
            "mem_ref",
            "view_convert_expr",
        ):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            stat_list.append(statement)
            return (True, None)

        if type_name == "array_ref":
            op0_entry = statement_entry.get("op 0")  ## element
            _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
            op1_entry = statement_entry.get("op 1")  ## index
            _valid, op1_expr = self._analyze_func(op1_entry, stat_list)
            return (True, f"{op0_expr}[{op1_expr}]")

        if type_name == "component_ref":
            op1_entry = statement_entry.get("op 1")
            member_name = get_entry_name(op1_entry, None)
            if member_name:
                return (True, member_name)
            ## access to unnamed member (base class)
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry, stat_list)

        if type_name == "indirect_ref":
            op_entry = statement_entry.get("op 0")
            _valid, op0_expr = self._analyze_func(op_entry, stat_list)
            return (True, f"(*{op0_expr})")

        ## tcc_exceptional
        if type_name in ("tree_vec", "static_assert"):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            stat_list.append(statement)
            return (True, None)

        if type_name == "constructor":
            # array and object initialization
            return self._handle_constructor(statement_entry, stat_list)

        if type_name == "statement_list":
            index_entries = get_index_entries(statement_entry)
            for index_item in index_entries:
                self._analyze_func(index_item, stat_list)
            return (True, None)

        ## tcc_declaration
        if type_name in ("label_decl"):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            stat_list.append(statement)
            return (True, None)

        if type_name == "function_decl":
            return self._handle_function(statement_entry, stat_list)

        if type_name == "result_decl":
            ### do nothing
            ##result_value = get_entry_name(statement_entry)
            return (True, None)

        if type_name in ("field_decl"):
            name = get_entry_repr(statement_entry)
            return (True, name)

        if type_name in ("parm_decl"):
            name = get_entry_name(statement_entry)
            return (True, name)

        if type_name in ("var_decl"):
            var_name = get_entry_name(statement_entry)
            # if var_name not in self.scope_vars:
            #     self.scope_vars.add(var_name)
            #     var_expr = self._handle_var(statement_entry, stat_list)
            #     var_node = TypedStatement(var_expr, StatementType.NODE)
            #     stat_list.append(var_node)
            return (True, var_name)

        ## tcc_vl_exp
        if type_name == "call_expr":
            return self._handle_call(statement_entry, stat_list)

        ## =========================

        _LOGGER.error("unhandled statement type %s %s", statement_entry.get_id(), type_name)

        node = TypedStatement(
            f"+++ unhandled statement {statement_entry.get_id()} {statement_entry.get_type()} +++", StatementType.NODE
        )
        node.color = "#orange"
        stat_list.append(node)
        return (False, None)

    def _handle_statement(self, statement_entry: Entry, stat_list: List[Any]) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_statement")
        if not is_code_class:
            return (False, None)

        type_name = statement_entry.get_type()

        if type_name == "try_block":
            self._handle_try_block(statement_entry, stat_list)
            return (True, None)

        ## case_label_expr - case from switch inside code block
        ## "for_stmt" does not exists?
        if type_name in ("if_stmt", "case_label_expr", "for_stmt", "while_stmt", "try_catch_expr", "do_stmt"):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            stat_list.append(statement)
            return (True, None)

        if type_name == "switch_expr":
            self._handle_switch(statement_entry, stat_list)
            return (True, None)

        if type_name == "return_expr":
            return self._handle_return(statement_entry, stat_list)

        if type_name in ("try_finally_expr"):
            try_entry = statement_entry.get("op 0")
            try_list: List[Statement] = []
            _valid, op0_expr = self._analyze_func(try_entry, try_list)
            if not try_list:
                try_list.append(TypedStatement(op0_expr))

            finally_entry = statement_entry.get("op 1")
            finally_list: List[Statement] = []
            _valid, op1_expr = self._analyze_func(finally_entry, finally_list)
            if not finally_list:
                finally_list.append(TypedStatement(op1_expr))

            try_fin_grp = StatementList()
            # try_fin_grp = LabeledGroup("try_finally")

            try_group = LabeledGroup("try", try_list)
            try_fin_grp.append(try_group)

            finally_group = LabeledGroup("finally", finally_list)
            try_fin_grp.append(finally_group)

            stat_list.append(try_fin_grp)
            return (True, None)

        if type_name in ("goto_expr"):
            labl_entry = statement_entry.get("labl")
            label_id = labl_entry.get_id()
            label_name = get_entry_name(labl_entry, default_ret=None)
            statement = TypedStatement(label_name, StatementType.GOTO)
            statement.items.append(label_id)
            stat_list.append(statement)
            return (True, None)

        if type_name in ("label_expr"):
            label_name_entry = statement_entry.get("name")
            label_id = label_name_entry.get_id()
            label_name = get_entry_name(statement_entry, default_ret=None)
            statement = TypedStatement(label_name, StatementType.GOTOLABEL)
            statement.items.append(label_id)
            stat_list.append(statement)
            return (True, None)

        if type_name in ("asm_expr"):
            label_name = get_entry_name(statement_entry)
            statement = TypedStatement("assembler expression", StatementType.NODE)
            statement.color = COLOR_NODE_NOTICE
            stat_list.append(statement)
            return (True, None)

        if type_name == "decl_expr":
            self.decl_expr_counter += 1
            if self.decl_expr_counter >= len(self.vars):
                return (True, None)
            var_name, decl_expr = self.vars[self.decl_expr_counter]
            if decl_expr:
                decl_node = TypedStatement(decl_expr, StatementType.NODE)
                stat_list.append(decl_node)
            self.scope_vars.add(var_name)
            return (True, None)

        return (False, None)

    def _handle_try_block(self, statement_entry: Entry, stat_list: List[Any]):
        body_entry = statement_entry.get("body")
        try_stat_list: List[Any] = []
        self._analyze_func(body_entry, try_stat_list)

        try_fin_grp = StatementList()
        # try_fin_grp = LabeledGroup("try_block")

        try_group = LabeledGroup("try", try_stat_list)
        try_fin_grp.append(try_group)

        hand_entry = statement_entry.get("hdlr")
        entries_list = get_index_entries(hand_entry)
        for hand_item in entries_list:
            catch_name = "..."
            hand_type_entry = hand_item.get("type")
            if hand_type_entry is not None:
                catch_name = get_entry_repr(hand_type_entry)
            hand_body_entry = hand_item.get("body")
            hand_stat_list: List[Any] = []
            self._analyze_func(hand_body_entry, hand_stat_list)
            catch_group = LabeledGroup(f"catch: {catch_name}", hand_stat_list)
            try_fin_grp.append(catch_group)

        stat_list.append(try_fin_grp)

    def _handle_const(self, statement_entry: Entry) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_constant")
        if not is_code_class:
            return (False, None)

        ## constants
        # "complex_cst",
        # "raw_data_cst",

        type_name = statement_entry.get_type()

        if type_name == "void_cst":
            ## do nothing
            return (True, None)

        entry_repr = get_entry_repr(statement_entry)
        return (True, entry_repr)

    def _handle_unary(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_unary")
        if not is_code_class:
            return (False, None)

        type_name = statement_entry.get_type()

        cast_op_data = OP_UNARY_CAST_DICT.get(type_name)
        if cast_op_data:
            cast_op = cast_op_data[0]
            op0_entry = statement_entry.get("op 0")
            _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
            var_type = statement_entry.get("type")
            var_type_name, var_type_mod = get_type_name_mod(var_type)
            type_label = var_type_name
            if var_type_mod is not None:
                type_label = f"{var_type_mod} {var_type_name}"
            if cast_op:
                return (True, f"{cast_op}<{type_label}>({op0_expr})")
            return (True, f"({type_label}){op0_expr}")

        op_data = OP_UNARY_DICT.get(type_name)
        if not op_data:
            raise RuntimeError(f"unhandled unary type {type_name}")

        op_sign_left, op_sign_right = op_data
        if not op_sign_left:
            op_sign_left = ""
        if not op_sign_right:
            op_sign_right = ""
        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        return (True, f"{op_sign_left}{op0_expr}{op_sign_right}")

    def _handle_binary(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_binary")
        if not is_code_class:
            return (False, None)

        stat_entry_type_name = statement_entry.get_type()
        stat_entry_sign = OP_BINARY_DICT.get(stat_entry_type_name)
        if stat_entry_sign is None:
            _LOGGER.warning("unhandled binary arithmetic expression: %s", stat_entry_type_name)
            return (False, None)

        ## convert binary tree into Reverse Polish Notation
        op_queue = []
        left_visited = set()
        ret_seq = []
        # prev_sign = None
        op_queue.append(statement_entry)
        while op_queue:
            curr_item = op_queue[0]

            curr_type_name = curr_item.get_type()
            op_data = OP_BINARY_DICT.get(curr_type_name)
            if op_data is None:
                op_queue.pop(0)
                _valid, op0_expr = self._analyze_func(curr_item, stat_list)
                continue

            op_sign = op_data[1]
            if op_sign is None:
                raise RuntimeError("invalid case: missing data")

            op_sign_start = op_data[0]
            if op_sign_start:
                ret_seq.append(op_sign_start)

            curr_id = curr_item.get_id()
            if curr_id not in left_visited:
                left_visited.add(curr_id)
                op0_entry = curr_item.get("op 0")
                op0_binary = is_entry_code_class(op0_entry, "tcc_binary")
                if op0_binary:
                    op_queue.insert(0, op0_entry)
                    continue

                _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
                if op0_expr is None:
                    # TODO: implement
                    # _LOGGER.warning("unhandled entry: %s %s", op0_entry.get_type(), op0_entry.get_id())
                    op0_expr = f"?!?{op0_entry.get_type()}{op0_entry.get_id()}"
                ret_seq.append(op0_expr)

            if op_data[0] and op_data[2]:
                ret_seq.append(op_sign)
            else:
                ret_seq.append(f" {op_sign} ")
            op_queue.pop(0)

            op1_entry = curr_item.get("op 1")
            op1_binary = is_entry_code_class(op1_entry, "tcc_binary")
            if op1_binary:
                op_queue.insert(0, op1_entry)
                continue

            # is_stronger = self._is_stronger(op_sign, prev_sign)
            # op_sign = prev_sign

            _valid, op1_expr = self._analyze_func(op1_entry, stat_list)
            if op1_expr is None:
                # TODO: implement
                # _LOGGER.warning("unhandled entry: %s %s", op1_entry.get_type(), op1_entry.get_id())
                op1_expr = f"?!?{op1_entry.get_type()}{op1_entry.get_id()}"

            # if is_stronger:
            #     ret_seq.append(op1_expr)
            # else:
            #     ret_seq.insert(0, "(")
            #     ret_seq.append(op1_expr)
            #     ret_seq.append(")")
            ret_seq.insert(0, "(")
            ret_seq.append(op1_expr)

            op_sign_end = op_data[2]
            if op_sign_start:
                ret_seq.append(op_sign_end)

            ret_seq.append(")")

        if ret_seq:
            ## remove unnecessary parenthesis
            ret_seq = ret_seq[1:]
            ret_seq = ret_seq[:-1]

        expr_str = "".join(ret_seq)
        return (True, expr_str)

    def _handle_comparison(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_comparison")
        if not is_code_class:
            return (False, None)

        type_name = statement_entry.get_type()
        op_data = OP_COMPARISON_DICT.get(type_name)
        if op_data is None:
            raise RuntimeError(f"unhandled comparison type {type_name}")

        op_sign = op_data[1]
        if op_sign is None:
            raise RuntimeError("invalid case: missing data")

        op_before = op_data[0]
        op_after = op_data[2]

        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        op1_entry = statement_entry.get("op 1")
        _valid, op1_expr = self._analyze_func(op1_entry, stat_list)

        if op_before and op_after:
            return (True, f"{op_before}{op0_expr}{op_sign}{op1_expr}{op_after}")
        return (True, f"{op0_expr} {op_sign} {op1_expr}")

    def _handle_expression(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        is_code_class = is_entry_code_class(statement_entry, "tcc_expression")
        if not is_code_class:
            return (False, None)

        other_valid_expr, other_name_exp = self._handle_expression_op1(statement_entry, stat_list)
        if other_valid_expr:
            return (True, other_name_exp)

        other_valid_expr, other_name_exp = self._handle_expression_op2(statement_entry, stat_list)
        if other_valid_expr:
            return (True, other_name_exp)

        type_name = statement_entry.get_type()

        if type_name == "predict_expr":
            ## hint for branch prediction - ignore
            return (True, None)

        if type_name == "cond_expr":
            self._handle_if(statement_entry, stat_list)
            return (True, None)

        if type_name == "init_expr":
            return self._handle_init(statement_entry, stat_list)

        if type_name == "compound_expr":
            op0_entry = statement_entry.get("op 0")
            _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
            if op0_expr:
                stat_list.append(TypedStatement(op0_expr))
            op1_entry = statement_entry.get("op 1")
            _valid, op1_expr = self._analyze_func(op1_entry, stat_list)
            return (True, f"{op1_expr}")

        # if type_name == "target_expr":
        #     decl_entry = statement_entry.get("decl")
        #     _valid, decl_expr = self._analyze_func(decl_entry, stat_list)
        #     init_entry = statement_entry.get("init")
        #     _valid, init_expr = self._analyze_func(init_entry, stat_list)
        #     return (True, f"{decl_expr}{init_expr}")

        if type_name == "addr_expr":
            op_entry = statement_entry.get("op 0")
            _valid, item_expr = self._analyze_func(op_entry, stat_list)
            if item_expr is not None:
                return (True, "(&" + item_expr + ")")
            return (True, None)

        if type_name == "bind_expr":
            # new scope
            scope_analysis = ScopeAnalysis(self.content)
            bind_list = scope_analysis.analyze(statement_entry)
            stat_list.extend(bind_list)
            return (True, None)

        if type_name == "must_not_throw_expr":
            body_entry = statement_entry.get("body")
            return self._analyze_func(body_entry, stat_list)

        if type_name == "expr_stmt":
            expr_entry = statement_entry.get("expr")
            _valid, expr = self._analyze_func(expr_entry, stat_list)
            if expr is not None:
                stat_list.append(TypedStatement(expr, StatementType.NODE))
            ## None happens when "[[fallthrough]];" is used explicit
            return (True, None)

        if type_name == "cleanup_point_expr":
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry, stat_list)

        if type_name == "save_expr":
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry, stat_list)

        if type_name in UNSUPPORTED_EXPRESSION_SET:
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            stat_list.append(statement)
            return (True, None)

        return (False, None)

    def _handle_expression_op1(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        type_name = statement_entry.get_type()
        op_data = OP1_EXPR_DICT.get(type_name)
        if not op_data:
            return (False, None)
        op_sign_left, op_sign_right = op_data
        if not op_sign_left:
            op_sign_left = ""
        if not op_sign_right:
            op_sign_right = ""
        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        return (True, f"{op_sign_left}{op0_expr}{op_sign_right}")

    def _handle_expression_op2(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        type_name = statement_entry.get_type()
        op_data = OP2_EXPR_DICT.get(type_name)
        if op_data is None:
            return (False, None)
        op_sign = op_data[1]
        if op_sign is None:
            raise RuntimeError("invalid case: missing data")

        op_before = op_data[0]
        op_after = op_data[2]

        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        op1_entry = statement_entry.get("op 1")
        _valid, op1_expr = self._analyze_func(op1_entry, stat_list)

        if op_before and op_after:
            return (True, f"{op_before}{op0_expr}{op_sign}{op1_expr}{op_after}")
        return (True, f"{op0_expr} {op_sign} {op1_expr}")

    def _handle_init(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        op1_entry = statement_entry.get("op 1")
        _valid, op1_expr = self._analyze_func(op1_entry, stat_list)
        if op0_expr is None:
            return (True, op1_expr)
        return (True, f"{op0_expr} = {op1_expr}")

    def _handle_return(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        expr_entry = statement_entry.get("expr")
        if expr_entry is None:
            stat_list.append(TypedStatement(None, StatementType.STOP))
            return (True, None)
        _valid, expr_expr = self._analyze_func(expr_entry, stat_list)
        ret_expr = f"return {expr_expr}"
        stat_list.append(TypedStatement(ret_expr, StatementType.STOP))
        return (True, None)

    def _handle_function(self, statement_entry: Entry, _stat_list: List[Statement]) -> Tuple[bool, str]:
        note_list = statement_entry.get_list("note")
        if "artificial" in note_list:
            ## skip artificial elements
            return (True, None)
        name_list = get_decl_namespace_list(statement_entry)
        func_name = "::".join(name_list)
        return (True, func_name)

    def _handle_call(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        func_name = "???"
        call_name, is_meth = self._get_call_expr_name(statement_entry)
        if call_name is not None:
            func_name = call_name
        else:
            fn_entry = statement_entry.get("fn")
            if fn_entry is not None:
                if fn_entry.get_type() == "obj_type_ref":
                    # virtual method call
                    is_meth = True
            else:
                ## fallthrough case
                return (True, None)
        params_list = []
        arg_entries = get_index_entries(statement_entry)
        for arg_item in arg_entries:
            _valid, arg_expr = self._analyze_func(arg_item, stat_list)
            if arg_expr is not None:
                params_list.append(arg_expr)
        obj_name = ""
        if is_meth:
            # in case of method first parameter is object
            # if not params_list:
            #     pass
            if params_list:
                first_param = params_list.pop(0)
                obj_name = f"{first_param}->"
            else:
                obj_name = "???->"
        params_str = ", ".join(params_list)
        return (True, f"{obj_name}{func_name}({params_str})")

    def _get_call_expr_name(self, call_expr_entry: Entry):
        func_decl = self._get_function_decl(call_expr_entry)
        if func_decl is None:
            return (None, False)
        fn_type = func_decl.get_type()
        if fn_type == "function_decl":
            return self._get_function_info(func_decl)

        if fn_type == "var_decl":
            var_name = get_entry_name(func_decl)
            return (var_name, False)

        if fn_type == "va_arg_expr":
            # happens when function pointer is taken by va_arg macro
            # and then when it's called
            return ("va_arg", False)

        _LOGGER.error("unhandled call type: %s %s in %s", fn_type, func_decl.get_id(), call_expr_entry.get_id())
        return (None, False)

    def _get_function_decl(self, call_expr_entry: Entry):
        expr_entry = call_expr_entry.get("fn")
        if expr_entry is None:
            ## happens when "[[fallthrough]];" is used explicit
            return None
        expr_type = expr_entry.get_type()
        if expr_type == "addr_expr":
            func_decl = expr_entry.get("op 0")
            if func_decl is None:
                # obj_type_ref - before the path there is only "type" field
                return None
            return func_decl
        if expr_type == "obj_type_ref":
            # try to get virtual method
            tok_entry = expr_entry.get("tok")
            if tok_entry is None:
                # missing tok entry - old version of GCC
                _LOGGER.warning("invalid node: obj_type_ref with missing 'tok' - please use GCC 15 or never")
                return None
            vtable_index = tok_entry.get("int")
            if vtable_index is None:
                _LOGGER.warning("invalid case")
                return None
            vtable_index = int(vtable_index) + 2
            base_class_ptr = tok_entry.get("type")
            if base_class_ptr is None:
                _LOGGER.warning("invalid case")
            base_class_record = base_class_ptr.get("ptd")
            if base_class_record is None:
                return None
            vtable_var = find_class_vtable_var_decl(self.content, base_class_record)
            if vtable_var is None:
                return None
            vtable_entries = get_vtable_entries(vtable_var)
            vfunc_decl = vtable_entries[vtable_index]
            return vfunc_decl
        if expr_type == "var_decl":
            return expr_entry

        if expr_type in EXPR_UNSUPPORTED_SET:
            # TODO: implement
            # _LOGGER.warning(f"unhandled call expression: {expr_type}")
            return None

        _LOGGER.error("unhandled expr type: %s %s in %s", expr_type, expr_entry.get_id(), call_expr_entry.get_id())
        return None

    def _get_function_info(self, func_decl: Entry):
        if func_decl is None:
            return (None, False)
        func_decl_type = func_decl.get_type()
        if func_decl_type not in ("function_decl"):
            _LOGGER.error("unhandled entry type: %s", func_decl_type)
            return (None, False)
        is_meth = is_method_of_instance(func_decl)
        if is_meth:
            func_name = get_entry_name(func_decl)
        else:
            func_name = get_entry_repr(func_decl)
        return (func_name, is_meth)

    def _handle_constructor(self, statement_entry: Entry, stat_list: List[Statement]) -> Tuple[bool, str]:
        init_list = []
        items_num = int(statement_entry.get("lngt"))
        data_list = statement_entry.get_ordered_tuples(["idx", "val"])
        if len(data_list) != items_num:
            raise RuntimeError("invalid number of values in entry: {statement_entry}")
        for index, data_item in enumerate(data_list):
            data_idx = data_item[0]
            data_val = data_item[1]
            idx_expr = str(index)
            if data_idx:
                valid_idx, idx_expr = self._analyze_func(data_idx, stat_list)
                if valid_idx is False:
                    idx_expr = str(index)
            _valid, val_expr = self._analyze_func(data_val, stat_list)
            item_expr = f"[{idx_expr}] = {val_expr}"
            init_list.append(item_expr)
        whole_expr = ", ".join(init_list)
        return (True, f"{{{whole_expr}}}")

    def _handle_if(self, statement_entry: Entry, stat_list: List[Statement]):
        op0_entry = statement_entry.get("op 0")
        _valid, op0_expr = self._analyze_func(op0_entry, stat_list)
        if_node = TypedStatement(op0_expr, StatementType.IF)

        true_stats: List[Statement] = []
        op1_entry = statement_entry.get("op 1")  ## true branch
        self._analyze_func(op1_entry, true_stats)
        if_node.items.append(true_stats)

        false_stats: List[Statement] = []
        op2_entry = statement_entry.get("op 2")  ## false branch
        self._analyze_func(op2_entry, false_stats)
        if_node.items.append(false_stats)

        stat_list.append(if_node)

    def _handle_switch(self, statement_entry: Entry, stat_list: List[Statement]):
        body_entry = statement_entry.get("body")
        subbody_entry = body_entry.get("0")
        if subbody_entry is None:
            # switch without any case and default
            return

        switch_node = SwitchStatement("")

        cond_entry = statement_entry.get("cond")
        _valid, cond_expr = self._analyze_func(cond_entry, [])
        switch_node.name = cond_expr

        if subbody_entry.get_type() == "bind_expr":
            body_entry = subbody_entry.get("body")

        index_entries = get_index_entries(body_entry)
        # entries_num = len(index_entries)
        # if entries_num % 2 != 0:
        #     raise RuntimeError(f"invalid number of operations in switch entry {statement_entry.get_id()}")
        #
        # for index in range(0, entries_num, 2):

        recent_case_value = None  # list of one element
        recent_case_fallthrough: bool = True
        recent_case_stats: List[Statement] = None

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
                        recent_case_fallthrough = True  ## can happen - two case_label_expr in row
                        recent_case_stats = None

                case_value_entry = case_entry.get("low")
                if case_value_entry is not None:
                    ## normal case
                    recent_case_value = [get_number_entry_value(case_value_entry)]
                else:
                    ## default case
                    recent_case_value = [None]
                continue

            if case_entry_type == "goto_expr":
                # break instruction
                recent_case_fallthrough = False
                continue

            if case_entry_type == "label_expr":
                recent_case_fallthrough = True
                continue

            ## add regular branch
            # TODO: is should be fixed, because "while" from ctrl_switch1.cpp" is missing
            recent_case_fallthrough = True
            recent_case_stats = []
            self._analyze_func(case_entry, recent_case_stats)

        if recent_case_value is not None:
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
        # return (case_value, is_fallthrough, case_statements)

    def _find_return_item(self, statements_list):
        for index, item in enumerate(statements_list):
            if item.type == StatementType.STOP:
                return index
        return -1


def get_vtable_entries(vtable_var_decl: Entry):
    tab_dict = {}
    var_init = vtable_var_decl.get("init")
    items_num = int(var_init.get("lngt"))
    data_list = var_init.get_ordered_tuples(["idx", "val"])
    if len(data_list) != items_num:
        raise RuntimeError("invalid number of values in entry: {statement_entry}")
    for index, data_item in enumerate(data_list):
        data_idx = data_item[0]
        data_val = data_item[1]
        idx_expr = index
        if data_idx:
            idx_expr = get_number_entry_value(data_idx)
            idx_expr = int(idx_expr)
        subval_entry = data_val.get("op 0")
        if subval_entry.get_type() == "addr_expr":
            subval_entry = subval_entry.get("op 0")
        tab_dict[idx_expr] = subval_entry
    return tab_dict


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
