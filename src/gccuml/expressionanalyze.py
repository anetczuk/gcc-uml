#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict, List, Tuple, Any, Set

from gccuml.langcontent import (
    LangContent,
    Entry,
    get_entry_name,
    get_number_entry_value,
    get_decl_namespace_list,
    get_type_entry_name,
    is_method_of_instance,
)
from gccuml.langanalyze import (
    find_class_vtable_var_decl,
    get_entry_repr,
    is_entry_code_class,
    get_vtable_entries,
)
from gccuml.diagram.activitydata import (
    StatementType,
    LabeledGroup,
    StatementList,
    SwitchStatement,
    TypedStatement,
    ActivityData,
    GotoStatement,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ==========================================================


COLOR_NODE_NOTICE = "orange"


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


class EntryExpression:

    def __init__(self, expression: str = None, statements: List[ActivityData] = None, valid: bool = None):
        self.valid: bool = False
        self.statements: List[ActivityData] = []  ## side effects
        self.expression: str = expression
        if expression is not None:
            self.valid = True
        if statements is not None:
            self.valid = True
            self.statements = statements
        if valid is not None:
            self.valid = valid

    def __bool__(self):
        return self.valid

    def get_all_statements(self):
        stat_list = self.statements.copy()
        stat = TypedStatement(self.expression)
        stat_list.append(stat)
        return stat_list


class SwitchContext:

    def __init__(self):
        self.switch_node: SwitchStatement = SwitchStatement("")
        self.break_id = None
        self.recent_case_value = None  # list consists of one element
        self.recent_case_fallthrough = True  # can happen - two case_label_expr in row
        self.recent_case_stats: List[ActivityData] = None

    def set_condition(self, cond_expr):
        self.switch_node.name = cond_expr

    def set_break_label(self, label_id):
        self.switch_node.break_label_id = label_id

    def is_break_label(self, label_id):
        return self.switch_node.break_label_id == label_id

    def handle_case_label_expr(self, case_label_expr_entry):
        self.add_recent_case()
        case_value_entry = case_label_expr_entry.get("low")
        label_id = case_label_expr_entry.get_id()
        if case_value_entry is not None:
            ## normal case
            case_value = get_number_entry_value(case_value_entry)
            self.recent_case_value = (label_id, case_value)
        else:
            ## default case
            self.recent_case_value = (label_id, None)

    def add_inner_case(self, label_id, case_value):
        self.switch_node.addon_labels.append((label_id, case_value))

    def add_recent_case(self):
        if self.recent_case_value is None:
            return
        ## fallthrough case
        case_data = self._get_switch_case()
        if case_data:
            self.switch_node.items.append(case_data)
            self.recent_case_value = None
            self.recent_case_fallthrough = True  ## can happen - two case_label_expr in row
            self.recent_case_stats = None

    def set_fallthrough(self, value):
        self.recent_case_fallthrough = value

    def add_statements(self, statements):
        if self.recent_case_value is None:
            # if not self.switch_node.items and self.recent_case_value is None:
            ## ignore statements without any case
            return

        self.recent_case_fallthrough = True
        if self.recent_case_stats:
            ## 'case' statement inside code
            self.recent_case_stats.extend(statements)
        else:
            self.recent_case_stats = statements

    def end_switch(self):
        self.add_recent_case()

    ## returns (case label value, is fallthrough, list of statements inside case)
    def _get_switch_case(self):
        label_id = self.recent_case_value[0]
        case_value = self.recent_case_value[1]

        if self.recent_case_stats is None:
            self.recent_case_stats = []
        return (label_id, case_value, self.recent_case_fallthrough, self.recent_case_stats)


class ScopeAnalysis:

    def __init__(self, content: LangContent):
        self.content = content
        self.vars: List[Tuple[str, str]] = []
        self.var_defs: Dict[str, Any] = {}
        self.scope_vars: Set[str] = set()

        ## 'case' expression of 'switch' can be nested inside code like 'goto' statement
        ## so we need to have access to it
        self.switch_stack: List[SwitchContext] = []

        self.decl_expr_counter = -1

    def analyze(self, statement_entry: Entry) -> List[ActivityData]:
        type_name = statement_entry.get_type()
        if type_name != "bind_expr":
            entry_expr = self._analyze_func(statement_entry)
            return entry_expr.statements
        # new scope
        self._read_var_defs(statement_entry)
        body_entry = statement_entry.get("body")
        entry_expr = self._analyze_func(body_entry)
        return entry_expr.statements

    def _read_var_defs(self, bind_expr: Entry):
        bind_vars = bind_expr.get_sub_entries("vars")
        for _var_prop, var_item in bind_vars:
            var_name = get_entry_name(var_item)
            decl_entry_expr = self.handle_var(var_item)
            decl_expr = decl_entry_expr.expression
            self.vars.append((var_name, decl_expr))

    def handle_var(self, var_decl: Entry) -> EntryExpression:
        var_name = get_entry_name(var_decl, None)
        if var_name is None:
            entry_id = var_decl.get_id()
            entry_id = entry_id.replace("@", "")
            var_name = f"__tmp_{entry_id}"
        var_type = var_decl.get("type")
        type_label = get_type_entry_name(var_type)

        init_entry = var_decl.get("init")
        if not init_entry:
            decl_expr = f"{type_label} {var_name}"
            return EntryExpression(decl_expr)
        init_entry_expr = self._analyze_func(init_entry)
        init_expr = init_entry_expr.expression
        if init_expr is None:
            decl_expr = f"{type_label} {var_name}"
        else:
            decl_expr = f"{type_label} {var_name} = {init_expr}"
        init_entry_expr.expression = decl_expr
        return init_entry_expr

    def _analyze_func(self, statement_entry: Entry) -> EntryExpression:
        if statement_entry is None:
            return EntryExpression()

        ## tcc_constant
        entry_expr = self._handle_const(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_unary
        entry_expr = self._handle_unary(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_binary
        entry_expr = self._handle_binary(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_comparison
        entry_expr = self._handle_comparison(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_statement
        entry_expr = self._handle_statement(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_expression
        entry_expr = self._handle_expression(statement_entry)
        if entry_expr:
            return entry_expr

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
            return EntryExpression(statements=[statement])

        if type_name == "array_ref":
            stat_list = []
            op0_entry = statement_entry.get("op 0")  ## element
            op0_entry_expr = self._analyze_func(op0_entry)
            stat_list.extend(op0_entry_expr.statements)
            op0_expr = op0_entry_expr.expression

            op1_entry = statement_entry.get("op 1")  ## index
            op1_entry_expr = self._analyze_func(op1_entry)
            stat_list.extend(op1_entry_expr.statements)
            op1_expr = op1_entry_expr.expression
            return EntryExpression(f"{op0_expr}[{op1_expr}]", stat_list)

        if type_name == "component_ref":
            op1_entry = statement_entry.get("op 1")
            member_name = get_entry_name(op1_entry, None)
            if member_name:
                return EntryExpression(member_name)
            ## access to unnamed member (base class)
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry)

        if type_name == "indirect_ref":
            op_entry = statement_entry.get("op 0")
            op0_entry_expr = self._analyze_func(op_entry)
            op0_expr = op0_entry_expr.expression
            op0_entry_expr.expression = f"(*{op0_expr})"
            return op0_entry_expr

        ## tcc_exceptional
        if type_name in ("tree_vec", "static_assert", "template_parm_index"):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            return EntryExpression(statements=[statement])

        if type_name == "constructor":
            # array and object initialization
            return self._handle_constructor(statement_entry)

        if type_name == "statement_list":
            index_entries = get_index_entries(statement_entry)
            stat_list = []
            for index_item in index_entries:
                item_entry_expr = self._analyze_func(index_item)
                stat_list.extend(item_entry_expr.statements)
            return EntryExpression(statements=stat_list)

        ## tcc_declaration
        entry_expr = self._handle_declaration(statement_entry)
        if entry_expr:
            return entry_expr

        ## tcc_vl_exp
        if type_name == "call_expr":
            return self._handle_call(statement_entry)

        if type_name == "aggr_init_expr":
            return self._handle_call(statement_entry)

        ## =========================

        _LOGGER.error("unhandled statement type %s %s", statement_entry.get_id(), type_name)

        node = TypedStatement(
            f"+++ unhandled statement {statement_entry.get_id()} {statement_entry.get_type()} +++", StatementType.NODE
        )
        node.color = "#orange"
        return EntryExpression(statements=[node])

    def _handle_statement(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_statement")
        if not is_code_class:
            return EntryExpression()

        type_name = statement_entry.get_type()

        if type_name == "try_block":
            try_entry_expr = EntryExpression(valid=True)
            self._handle_try_block(statement_entry, try_entry_expr.statements)
            return try_entry_expr

        ## case_label_expr - case from switch inside code block
        ## "for_stmt" does not exists?
        if type_name in ("if_stmt", "for_stmt", "while_stmt", "try_catch_expr", "do_stmt"):
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            return EntryExpression(statements=[statement])

        if type_name == "goto_expr":
            labl_entry = statement_entry.get("labl")
            label_id = labl_entry.get_id()

            visible = True
            switch_context: SwitchContext = None
            if self.switch_stack:
                switch_context = self.switch_stack[-1]
                if switch_context.is_break_label(label_id):
                    visible = False

            label_name = get_entry_name(labl_entry, default_ret=None)
            if label_name is None:
                label_name = label_id
            goto_statement = GotoStatement(label_name)
            goto_statement.label_id = label_id
            goto_statement.visible = visible
            return EntryExpression(statements=[goto_statement])

        if type_name == "label_expr":
            label_name_entry = statement_entry.get("name")
            label_id = label_name_entry.get_id()
            label_name = get_entry_name(statement_entry, default_ret=None)
            if label_name is None:
                label_name = label_id
            statement = TypedStatement(label_name, StatementType.GOTOLABEL)
            statement.items.append(label_id)
            return EntryExpression(statements=[statement])

        if type_name == "case_label_expr":
            if not self.switch_stack:
                _LOGGER.warning("unexpected case_label_expr - outside of 'switch' scope ")
                statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
                return EntryExpression(statements=[statement])

            # switch_context: SwitchContext
            switch_context = self.switch_stack[-1]

            case_value_entry = statement_entry.get("low")
            case_value = None
            if case_value_entry is not None:
                ## normal case
                case_value = get_number_entry_value(case_value_entry)
            label_id = statement_entry.get_id()
            if case_value is None:
                case_value = label_id
            switch_context.add_inner_case(label_id, case_value)
            statement = TypedStatement(case_value, StatementType.GOTOLABEL)
            statement.items.append(label_id)
            statement.items.append(False)
            return EntryExpression(statements=[statement])

        if type_name == "switch_expr":
            return self._handle_switch(statement_entry)

        if type_name == "return_expr":
            return self._handle_return(statement_entry)

        if type_name in ("try_finally_expr"):
            try_entry = statement_entry.get("op 0")
            op0_entry_expr = self._analyze_func(try_entry)
            op0_expr = op0_entry_expr.expression
            try_list = op0_entry_expr.statements
            if not try_list:
                try_list.append(TypedStatement(op0_expr))

            finally_entry = statement_entry.get("op 1")
            op1_entry_expr = self._analyze_func(finally_entry)
            finally_list = op1_entry_expr.statements
            op1_expr = op1_entry_expr.expression
            if not finally_list:
                finally_list.append(TypedStatement(op1_expr))

            try_fin_grp = StatementList()
            # try_fin_grp = LabeledGroup("try_finally")

            try_group = LabeledGroup("try", try_list)
            try_fin_grp.append(try_group)

            finally_group = LabeledGroup("finally", finally_list)
            try_fin_grp.append(finally_group)

            return EntryExpression(statements=[try_fin_grp])

        if type_name in ("asm_expr"):
            # label_name = get_entry_name(statement_entry)
            statement = TypedStatement("assembler expression", StatementType.NODE)
            statement.color = COLOR_NODE_NOTICE
            return EntryExpression(statements=[statement])

        if type_name == "decl_expr":
            self.decl_expr_counter += 1
            if self.decl_expr_counter >= len(self.vars):
                return EntryExpression(valid=True)
            var_name, decl_expr = self.vars[self.decl_expr_counter]
            entry_stat = EntryExpression(valid=True)
            if decl_expr:
                decl_node = TypedStatement(decl_expr, StatementType.NODE)
                entry_stat.statements.append(decl_node)
            self.scope_vars.add(var_name)
            return entry_stat

        return EntryExpression()

    def _handle_try_block(self, statement_entry: Entry, stat_list: List[Any]):
        body_entry = statement_entry.get("body")
        try_entry_expr = self._analyze_func(body_entry)
        try_stat_list = try_entry_expr.statements

        try_fin_grp = StatementList()
        # try_fin_grp = LabeledGroup("try_block")

        try_group = LabeledGroup("try", try_stat_list)
        try_fin_grp.append(try_group)

        hand_entry = statement_entry.get("hdlr")
        entries_list = get_index_entries(hand_entry)
        for hand_item in entries_list:
            catch_name = "..."
            # hand_type_entry = hand_item.get("type")
            # if hand_type_entry is not None:
            #     catch_name = get_entry_repr(hand_type_entry)
            hand_body_entry = hand_item.get("body")
            hand_vars_entry = hand_body_entry.get("vars")
            if hand_vars_entry is not None:
                hand_vars_type_entry = hand_vars_entry.get("type")
                catch_type = get_entry_repr(hand_vars_type_entry)
                catch_name = get_entry_name(hand_vars_entry, None)
                if catch_name is None:
                    catch_name = catch_type
                else:
                    catch_name = f"{catch_type} {catch_name}"
            hand_body_entry = hand_body_entry.get("body")
            body_entry_expr = self._analyze_func(hand_body_entry)
            hand_stat_list = body_entry_expr.statements
            catch_group = LabeledGroup(f"catch: {catch_name}", hand_stat_list)
            try_fin_grp.append(catch_group)

        stat_list.append(try_fin_grp)

    def _handle_const(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_constant")
        if not is_code_class:
            return EntryExpression()

        ## constants
        # "complex_cst",
        # "raw_data_cst",

        type_name = statement_entry.get_type()

        if type_name == "void_cst":
            ## do nothing
            return EntryExpression("void")

        entry_repr = get_entry_repr(statement_entry)
        return EntryExpression(entry_repr)

    def _handle_unary(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_unary")
        if not is_code_class:
            return EntryExpression()

        type_name = statement_entry.get_type()

        cast_op_data = OP_UNARY_CAST_DICT.get(type_name)
        if cast_op_data:
            cast_op = cast_op_data[0]
            op0_entry = statement_entry.get("op 0")
            op0_entry_expr = self._analyze_func(op0_entry)
            op0_expr = op0_entry_expr.expression
            var_type = statement_entry.get("type")
            type_label = get_type_entry_name(var_type)
            if cast_op:
                return EntryExpression(f"{cast_op}<{type_label}>({op0_expr})", op0_entry_expr.statements)
            return EntryExpression(f"({type_label}){op0_expr}", op0_entry_expr.statements)

        op_data = OP_UNARY_DICT.get(type_name)
        if not op_data:
            raise RuntimeError(f"unhandled unary type {type_name}")

        op_sign_left, op_sign_right = op_data
        if not op_sign_left:
            op_sign_left = ""
        if not op_sign_right:
            op_sign_right = ""
        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        op0_expr = op0_entry_expr.expression
        return EntryExpression(f"{op_sign_left}{op0_expr}{op_sign_right}", op0_entry_expr.statements)

    def _handle_binary(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_binary")
        if not is_code_class:
            return EntryExpression()

        stat_entry_type_name = statement_entry.get_type()
        stat_entry_sign = OP_BINARY_DICT.get(stat_entry_type_name)
        if stat_entry_sign is None:
            _LOGGER.warning("unhandled binary arithmetic expression: %s", stat_entry_type_name)
            return EntryExpression()

        stat_list: List[ActivityData] = []

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
                op0_entry_expr = self._analyze_func(curr_item)
                stat_list.extend(op0_entry_expr.statements)
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

                op0_entry_expr = self._analyze_func(op0_entry)
                stat_list.extend(op0_entry_expr.statements)
                op0_expr = op0_entry_expr.expression
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

            op1_entry_expr = self._analyze_func(op1_entry)
            stat_list.extend(op1_entry_expr.statements)
            op1_expr = op1_entry_expr.expression
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
        return EntryExpression(expr_str, stat_list)

    def _handle_comparison(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_comparison")
        if not is_code_class:
            return EntryExpression()

        type_name = statement_entry.get_type()
        op_data = OP_COMPARISON_DICT.get(type_name)
        if op_data is None:
            raise RuntimeError(f"unhandled comparison type {type_name}")

        op_sign = op_data[1]
        if op_sign is None:
            raise RuntimeError("invalid case: missing data")

        op_before = op_data[0]
        op_after = op_data[2]

        stat_list: List[ActivityData] = []

        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        stat_list.extend(op0_entry_expr.statements)
        op0_expr = op0_entry_expr.expression

        op1_entry = statement_entry.get("op 1")
        op1_entry_expr = self._analyze_func(op1_entry)
        stat_list.extend(op1_entry_expr.statements)
        op1_expr = op1_entry_expr.expression

        if op_before and op_after:
            return EntryExpression(f"{op_before}{op0_expr}{op_sign}{op1_expr}{op_after}")
        return EntryExpression(f"{op0_expr} {op_sign} {op1_expr}", stat_list)

    def _handle_expression(self, statement_entry: Entry) -> EntryExpression:
        is_code_class = is_entry_code_class(statement_entry, "tcc_expression")
        if not is_code_class:
            return EntryExpression()

        other_entry_exp = self._handle_expression_op1(statement_entry)
        if other_entry_exp:
            return other_entry_exp

        other_entry_exp = self._handle_expression_op2(statement_entry)
        if other_entry_exp:
            return other_entry_exp

        type_name = statement_entry.get_type()

        if type_name == "predict_expr":
            ## hint for branch prediction - ignore
            return EntryExpression(valid=True)

        if type_name == "cond_expr":
            ## if expression and ternary operator

            op1_entry = statement_entry.get("op 1")
            op2_entry = statement_entry.get("op 2")
            op1_type = op1_entry.get_type()
            op2_type = op2_entry.get_type()
            op_set = set([op1_type, op2_type])
            type_set = set(["cleanup_point_expr", "bind_expr", "return_expr", "statement_list"])
            if op_set.intersection(type_set):
                ## regular "if" expression
                if_entry_expr = EntryExpression(valid=True)
                self._handle_if(statement_entry, if_entry_expr.statements)
                return if_entry_expr

            ## ternary operator
            ternary_expr = self._handle_ternary(statement_entry)
            if ternary_expr is not None:
                return ternary_expr

            ## regular "if" expression
            if_entry_expr = EntryExpression(valid=True)
            self._handle_if(statement_entry, if_entry_expr.statements)
            return if_entry_expr

        if type_name == "init_expr":
            return self._handle_init(statement_entry)

        if type_name == "compound_expr":
            stat_list = []
            op0_entry = statement_entry.get("op 0")  # the first value is ignored
            op0_entry_expr = self._analyze_func(op0_entry)
            stat_list.extend(op0_entry_expr.statements)
            op0_expr = op0_entry_expr.expression
            if op0_expr:
                stat_list.append(TypedStatement(op0_expr))
            op1_entry = statement_entry.get("op 1")  # the second value is used
            op1_entry_expr = self._analyze_func(op1_entry)
            stat_list.extend(op1_entry_expr.statements)
            op1_expr = op1_entry_expr.expression
            return EntryExpression(f"{op1_expr}", stat_list)

        if type_name == "target_expr":
            decl_entry = statement_entry.get("decl")
            decl_expr: EntryExpression = self._analyze_func(decl_entry)
            init_entry = statement_entry.get("init")
            init_expr: EntryExpression = self._analyze_func(init_entry)
            if not decl_expr or not decl_expr.expression:
                expr = init_expr.expression
                return EntryExpression(expr)
            expr = decl_expr.expression + " = " + init_expr.expression
            return EntryExpression(expr)

        if type_name == "addr_expr":
            op_entry = statement_entry.get("op 0")
            item_entry_expr = self._analyze_func(op_entry)
            item_expr = item_entry_expr.expression
            if item_expr is not None:
                item_entry_expr.expression = "(&" + item_expr + ")"
            return item_entry_expr

        if type_name == "bind_expr":
            # new scope
            # scope_analysis = ScopeAnalysis(self.content)
            # bind_list = scope_analysis.analyze(statement_entry)
            bind_list = self.analyze(statement_entry)
            return EntryExpression(statements=bind_list)

        if type_name == "must_not_throw_expr":
            body_entry = statement_entry.get("body")
            return self._analyze_func(body_entry)

        if type_name == "expr_stmt":
            stat_list = []
            expr_entry = statement_entry.get("expr")
            entry_expr = self._analyze_func(expr_entry)
            stat_list.extend(entry_expr.statements)
            expr = entry_expr.expression
            if expr is not None:
                stat_list.append(TypedStatement(expr, StatementType.NODE))
            ## None happens when "[[fallthrough]]" is used explicit
            return EntryExpression(statements=stat_list)

        if type_name == "cleanup_point_expr":
            ## new scope
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry)

        if type_name == "save_expr":
            op0_entry = statement_entry.get("op 0")
            return self._analyze_func(op0_entry)

        if type_name in UNSUPPORTED_EXPRESSION_SET:
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            return EntryExpression(statements=[statement])

        return EntryExpression()

    def _handle_expression_op1(self, statement_entry: Entry) -> EntryExpression:
        type_name = statement_entry.get_type()
        op_data = OP1_EXPR_DICT.get(type_name)
        if not op_data:
            return EntryExpression()
        op_sign_left, op_sign_right = op_data
        if not op_sign_left:
            op_sign_left = ""
        if not op_sign_right:
            op_sign_right = ""
        op0_entry = statement_entry.get("op 0")
        op0_entry_expr: EntryExpression = self._analyze_func(op0_entry)
        op0_expr = op0_entry_expr.expression
        op0_expr = f"{op_sign_left}{op0_expr}{op_sign_right}"
        op0_entry_expr.expression = op0_expr
        return op0_entry_expr

    def _handle_expression_op2(self, statement_entry: Entry) -> EntryExpression:
        type_name = statement_entry.get_type()
        op_data = OP2_EXPR_DICT.get(type_name)
        if op_data is None:
            return EntryExpression()
        op_sign = op_data[1]
        if op_sign is None:
            raise RuntimeError("invalid case: missing data")

        op_before = op_data[0]
        op_after = op_data[2]

        stat_list: List[ActivityData] = []

        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        stat_list.extend(op0_entry_expr.statements)
        op0_expr = op0_entry_expr.expression

        op1_entry = statement_entry.get("op 1")
        op1_entry_expr = self._analyze_func(op1_entry)
        stat_list.extend(op1_entry_expr.statements)
        op1_expr = op1_entry_expr.expression

        if op_before and op_after:
            return EntryExpression(f"{op_before}{op0_expr}{op_sign}{op1_expr}{op_after}", stat_list)
        return EntryExpression(f"{op0_expr} {op_sign} {op1_expr}", stat_list)

    def _handle_declaration(self, statement_entry: Entry) -> EntryExpression:
        type_name = statement_entry.get_type()

        if type_name == "label_decl":
            statement = TypedStatement(f"{type_name} {statement_entry.get_id()}", StatementType.UNSUPPORTED)
            return EntryExpression(statements=[statement])

        if type_name == "function_decl":
            return self._handle_function(statement_entry)

        if type_name == "result_decl":
            ### do nothing
            ##result_value = get_entry_name(statement_entry)
            return EntryExpression(valid=True)

        if type_name == "field_decl":
            name = get_entry_repr(statement_entry)
            return EntryExpression(name)

        if type_name == "parm_decl":
            name = get_entry_name(statement_entry)
            return EntryExpression(name)

        if type_name == "var_decl":
            var_name = get_entry_name(statement_entry, None)
            if var_name is None:
                ## case of GCC temporary variable
                # stat_init = statement_entry.get("init")
                # if stat_init is None:
                #     return EntryExpression("")
                entry_id = statement_entry.get_id()
                entry_id = entry_id.replace("@", "")
                var_name = f"__tmp_{entry_id}"

            if any(pair[0] == var_name for pair in self.vars):
                return EntryExpression(var_name)

            if var_name in self.scope_vars:
                return EntryExpression(var_name)

            ## first use - with initialization
            self.scope_vars.add(var_name)
            # return EntryExpression(var_name)

            # stat_type_entry = statement_entry.get("type")
            # var_type = get_entry_repr(stat_type_entry)
            # expr = f"{var_type} {var_name}"
            # return EntryExpression(expr)

            var_expr: EntryExpression = self.handle_var(statement_entry)
            stat_list = var_expr.get_all_statements()
            # return EntryExpression(var_expr.expression, stat_list)

            stat_init = statement_entry.get("init")
            if stat_init is not None:
                return EntryExpression(var_name, stat_list)

            stat_type_entry = statement_entry.get("type")
            var_type = get_entry_repr(stat_type_entry)
            expr = f"{var_type} {var_name}"
            return EntryExpression(expr, stat_list)
            # return EntryExpression(var_name, stat_list)

        return EntryExpression()

    def _handle_init(self, statement_entry: Entry) -> EntryExpression:
        stat_list: List[ActivityData] = []

        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        stat_list.extend(op0_entry_expr.statements)
        op0_expr = op0_entry_expr.expression

        op1_entry = statement_entry.get("op 1")
        op1_entry_expr = self._analyze_func(op1_entry)
        stat_list.extend(op1_entry_expr.statements)
        op1_expr = op1_entry_expr.expression

        if op0_expr is None:
            return EntryExpression(op1_expr, stat_list)
        return EntryExpression(f"{op0_expr} = {op1_expr}", stat_list)

    def _handle_return(self, statement_entry: Entry) -> EntryExpression:
        expr_entry = statement_entry.get("expr")
        if expr_entry is None:
            stop_stat = TypedStatement(None, StatementType.STOP)
            return EntryExpression(statements=[stop_stat])

        expr_entry_expr = self._analyze_func(expr_entry)
        expr_expr = expr_entry_expr.expression
        ret_expr = f"return {expr_expr}"
        stop_stat = TypedStatement(ret_expr, StatementType.STOP)
        expr_entry_expr.statements.append(stop_stat)
        return EntryExpression(expr_expr, expr_entry_expr.statements)

    def _handle_function(self, statement_entry: Entry) -> EntryExpression:
        note_list = statement_entry.get_list("note")
        if "artificial" in note_list:
            ## skip artificial elements
            return EntryExpression(valid=True)
        name_list = get_decl_namespace_list(statement_entry)
        func_name = "::".join(name_list)
        return EntryExpression(func_name)

    def _handle_call(self, statement_entry: Entry) -> EntryExpression:
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
                return EntryExpression(valid=True)

        stat_list: List[ActivityData] = []
        params_list = []
        arg_entries = get_index_entries(statement_entry)
        for arg_item in arg_entries:
            arg_entry_expr = self._analyze_func(arg_item)
            stat_list.extend(arg_entry_expr.statements)
            arg_expr = arg_entry_expr.expression
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
        return EntryExpression(f"{obj_name}{func_name}({params_str})", stat_list)

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

    def _get_function_decl(self, call_expr_entry: Entry) -> Entry:
        expr_entry = call_expr_entry.get("fn")
        if expr_entry is None:
            ## happens when "[[fallthrough]]" is used explicit
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
            vtable_var: Entry = find_class_vtable_var_decl(self.content, base_class_record)
            if vtable_var is None:
                return None
            vtable_entries: Dict[int, Entry] = get_vtable_entries(vtable_var)
            vfunc_decl: Entry = vtable_entries[vtable_index]
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

    def _handle_constructor(self, statement_entry: Entry) -> EntryExpression:
        init_list = []
        items_num = int(statement_entry.get("lngt"))
        data_list = statement_entry.get_ordered_tuples(["idx", "val"])
        if len(data_list) != items_num:
            raise RuntimeError("invalid number of values in entry: {statement_entry}")
        # stat_list: List[ActivityData] = []
        for index, data_item in enumerate(data_list):
            data_idx = data_item[0]
            data_val = data_item[1]
            idx_expr = str(index)
            if data_idx:
                idx_entry_expr = self._analyze_func(data_idx)
                # stat_list.extend(idx_entry_expr.statements)
                idx_expr = idx_entry_expr.expression
                if not idx_entry_expr:
                    idx_expr = str(index)
            val_entry_expr = self._analyze_func(data_val)
            # stat_list.extend(val_entry_expr.statements)
            val_expr = val_entry_expr.expression
            item_expr = f"[{idx_expr}] = {val_expr}"
            init_list.append(item_expr)
        whole_expr = ", ".join(init_list)
        return EntryExpression(f"{{{whole_expr}}}")

    def _handle_if(self, statement_entry: Entry, stat_list: List[ActivityData]):
        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        stat_list.extend(op0_entry_expr.statements)
        op0_expr = op0_entry_expr.expression
        if_node = TypedStatement(op0_expr, StatementType.IF)

        op1_entry = statement_entry.get("op 1")  ## true branch
        op1_entry_expr = self._analyze_func(op1_entry)
        true_stats = op1_entry_expr.statements
        if_node.items.append(true_stats)

        op2_entry = statement_entry.get("op 2")  ## false branch
        op2_entry_expr = self._analyze_func(op2_entry)
        false_stats = op2_entry_expr.statements
        if_node.items.append(false_stats)

        stat_list.append(if_node)

    def _handle_ternary(self, statement_entry: Entry):
        op0_entry = statement_entry.get("op 0")
        op0_entry_expr = self._analyze_func(op0_entry)
        op0_expr = op0_entry_expr.expression

        op1_entry = statement_entry.get("op 1")  ## true branch
        op1_entry_expr = self._analyze_func(op1_entry)
        true_stats = op1_entry_expr.expression
        if true_stats is None:
            ## will fallthrough to IF handler
            return None

        op2_entry = statement_entry.get("op 2")  ## false branch
        op2_entry_expr = self._analyze_func(op2_entry)
        false_stats = op2_entry_expr.expression
        if false_stats is None:
            ## will fallthrough to IF handler
            return None

        ternary_expr = f"{op0_expr} ? {true_stats} : {false_stats}"
        return EntryExpression(ternary_expr)

    def _handle_switch(self, statement_entry: Entry) -> EntryExpression:
        body_entry = statement_entry
        while True:
            next_body_entry = body_entry.get("body")
            if next_body_entry is None:
                break
            body_entry = next_body_entry

        subbody_entry = body_entry.get("0")
        if subbody_entry is None:
            # switch without any case and default
            return EntryExpression(valid=True)

        switch_context = SwitchContext()
        self.switch_stack.append(switch_context)

        cond_entry = statement_entry.get("cond")
        cond_entry_expr = self._analyze_func(cond_entry)
        cond_expr = cond_entry_expr.expression
        switch_context.set_condition(cond_expr)

        if subbody_entry.get_type() == "bind_expr":
            body_entry = subbody_entry.get("body")

        index_entries = get_index_entries(body_entry)

        for case_entry in index_entries:
            case_entry_type = case_entry.get_type()
            if case_entry_type == "label_expr":
                # break target label
                label_name_entry = case_entry.get("name")
                break_id = label_name_entry.get_id()
                switch_context.set_break_label(break_id)
                break

        for case_entry in index_entries:
            case_entry_type = case_entry.get_type()
            if case_entry_type == "case_label_expr":
                switch_context.handle_case_label_expr(case_entry)
                continue

            if case_entry_type == "goto_expr":
                # break instruction
                switch_context.set_fallthrough(False)
                continue

            if case_entry_type == "label_expr":
                # break target label
                switch_context.set_fallthrough(True)
                continue

            ## add regular branch
            # TODO: is should be fixed, because "while" from ctrl_switch1.cpp" is missing
            entry_expr = self._analyze_func(case_entry)
            case_stats = entry_expr.statements
            switch_context.add_statements(case_stats)

        switch_context.end_switch()

        switch_node = switch_context.switch_node
        self.switch_stack.pop()  ## remove current switch from stack

        return EntryExpression(statements=[switch_node])

    def _get_switch_case(self, case_value, is_fallthrough, case_statements):
        if case_statements is None:
            case_statements = []
        return (case_value, is_fallthrough, case_statements)

    def _find_return_item(self, statements_list):
        for index, item in enumerate(statements_list):
            if item.type == StatementType.STOP:
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
