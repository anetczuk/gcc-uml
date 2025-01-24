# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from enum import Enum, auto
from typing import NamedTuple, Any

from typing import List, Dict

from showgraph.io import write_file


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ===========================================================


class StatementType(Enum):
    NODE = auto()
    IF = auto()
    SWITCH = auto()
    STOP = auto()


class Statement:
    """Container for function data to be presented on graph.
    
    Depending on 'type' it can be 
    """

    def __init__(self, statement_name: str, statement_type: StatementType = StatementType.NODE):
        self.name: str = statement_name
        self.type: StatementType = statement_type
        self.color: str = None
        self.items: List[Any] = []


class StatementList:
    
    def __init__(self):
        self.items: List[Any] = []


FunctionArg = NamedTuple("FunctionArg", [("name", str), ("type", str)])


class LabeledCard:
    """Container for function data to be presented on graph.
    
    Item is presented as group/card.
    """

    def __init__(self, label: str = None):
        self.label = label
        self.subitems: List[Any] = None

    def set_label(self, func_name: str, args_list: List[FunctionArg], returntype: str):
        join_list = []
        for arg_item in args_list:
            if arg_item.name:
                join_list.append(f"{arg_item.type} {arg_item.name}")
            else:
                join_list.append(f"{arg_item.type} /*anonym*/")
                # args_list.append(arg_item.type)
        args_string = ", ".join(join_list)
        self.label = f"""{func_name}({args_string}) -> {returntype}"""


class LabeledGroup:
    """Container for function data to be presented on graph."""

    def __init__(self, label: str = None, subitems=None):
        self.label = label
        self.subitems: List[Any] = subitems
        if self.subitems is None:
            self.subitems = []


class SubNodeList:

    def __init__(self):
        self.subitems: List[Any] = []

    def append(self, item):
        self.subitems.append(item)


class SubGraph:

    def __init__(self, label=None, items_list=None):
        self.label: str = label
        self.subitems: List[Any] = items_list
        if self.subitems is None:
            self.subitems = []

    def append(self, item):
        self.subitems.append(item)


## ===========================================================


## Generator for PlantUml activity diagrams
class ActivityDiagramGenerator:

    def __init__(self, data_dict=None):
        self.data: Dict[str, LabeledCard] = data_dict
        if self.data is None:
            self.data = {}
        self.content_list: List[str] = []

    def generate(self, out_path):
        self.content_list = []
        if not self.data:
            ## empty data
            content = """\
@startuml
floating note left: Empty graph
stop
@enduml
"""
            _LOGGER.info("writing output to file %s", out_path)
            write_file(out_path, content)
            return

        # generate
        self.content_list = []
        self.content_list.append(
            """\
@startuml
"""
        )

        items_list = self.data.values()
        self._handle_list(items_list, 0)

        ##
        ## close diagram
        ##
        self.content_list.append("\n@enduml\n")
        content = "\n".join(self.content_list)

        # print(f"\ndiagram:\n{content}")

        _LOGGER.info("writing output to file %s", out_path)
        write_file(out_path, content)

    def _handle_list(self, items_list, indent=0):
        for stat in items_list:
            self._handle_item(stat, indent)

    def _handle_item(self, item, indent=1):
        if isinstance(item, SubGraph):
            self._handle_subgraph(item, indent)
            return

        if isinstance(item, SubNodeList):
            self._handle_subnodelist(item, indent)
            return

        if isinstance(item, LabeledCard):
            self._handle_card(item, indent)
            return

        if isinstance(item, LabeledGroup):
            self._handle_group(item, indent)
            return

        if isinstance(item, Statement):
            self._handle_statement(item, indent)
            return

        if isinstance(item, StatementList):
            self._handle_list(item.items, indent)
            return

        raise RuntimeError(f"unhandled item type: {type(item)}")

    def _handle_subgraph(self, node: SubGraph, indent=1):
        indent_str = "    " * indent
        self.content_list.append(
                f"""\
{indent_str}{{{{
{indent_str}    mainframe {node.label}"""
            )

        for subitem in node.subitems:
            self.content_list.append(f"{indent_str}    -[hidden]->")
            self._handle_item(subitem, indent + 1)

        self.content_list.append(
            f"""\
{indent_str}}}}}"""
        )

    def _handle_subnodelist(self, node: SubGraph, indent=1):
        indent_str = "    " * indent
        self.content_list.append(
                f"""\
{indent_str}:"""
            )

        for subitem in node.subitems:
            self._handle_item(subitem, indent + 1)

        self.content_list.append(
            f"""\
{indent_str};"""
        )

    def _handle_card(self, node: LabeledCard, indent=1):
        indent_str = "    " * indent

        func_label = node.label
        self.content_list.append(
            f"""\
{indent_str}card "{func_label}" {{"""
        )
#         self.content_list.append(
#             f"""\
# {indent_str}card "{func_label}" {{
# {indent_str}    start"""
#         )

        func_statements = node.subitems
        self._handle_list(func_statements, indent + 1)

        self.content_list.append(
            f"""\
{indent_str}    -[hidden]->
{indent_str}}}
"""
        )

    def _handle_group(self, node: LabeledGroup, indent=1):
        indent_str = "    " * indent

        func_label = node.label
        self.content_list.append(
            f"""\
{indent_str}group {func_label}"""
        )

        func_statements = node.subitems
        self._handle_list(func_statements, indent + 1)

        self.content_list.append(
            f"""\
{indent_str}end group
"""
        )

    def _handle_statement(self, statement: Statement, indent=1):
        indent_str = "    " * indent
        if statement.type == StatementType.NODE:
            color = statement.color
            if color is None:
                color = ""

            self.content_list.append(
                f"""\
{indent_str}{color}:{statement.name};"""
                )
            return

        if statement.type == StatementType.STOP:
            if statement.name:
                self.content_list.append(
                    f"""\
{indent_str}#lightgreen:{statement.name};"""
                    )
            self.content_list.append(
                f"""\
{indent_str}stop"""
                )
            return

        if statement.type == StatementType.IF:
            items_len = len(statement.items)
            if items_len != 2:
                raise RuntimeError(f"invalid IF node: required 2 items, got {items_len}")
            true_branch = statement.items[0]
            false_branch = statement.items[1]
            self.content_list.append(
                f"""\
{indent_str}if ({statement.name} ?) then (true)"""
            )
            self._handle_list(true_branch, indent=indent + 1)
            self.content_list.append(
                f"""\
{indent_str}else (false)"""
            )
            self._handle_list(false_branch, indent=indent + 1)
            self.content_list.append(
                f"""\
{indent_str}endif"""
            )
            return

        if statement.type == StatementType.SWITCH:
            items_num = len(statement.items)
            if items_num < 1:
                # no cases
                return

            ## switch start
            self.content_list.append(
                f"""
partition "switch:\\n{statement.name}" {{"""
            )

            nest_level = 0
            found_default = None

            for case_item in statement.items:
                case_value = case_item[0]
                case_fallthrough = case_item[1]
                case_statements = case_item[2]

                switch_indent_level = indent + nest_level
                switch_indent_str = "    " * switch_indent_level

                self.content_list.append(
                    f"""\
{switch_indent_str}' case: {case_value} fallthrough: {case_fallthrough}"""
                )

                if case_value is None:
                    found_default = case_statements
                    continue

                label_str = f"{case_value} ?"

                if case_fallthrough:
                    ## fallthrough
                    self.content_list.append(
                        f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                    )
                    self._handle_list(case_statements, indent=switch_indent_level + 1)
                    self.content_list.append(
                        f"""\
{switch_indent_str}endif"""
                    )
                    self.content_list.append(
                        f"""\
{switch_indent_str}note right: [fallthrough]"""
                    )
                else:
                    ## normal or default
                    self.content_list.append(
                        f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                    )
                    self._handle_list(case_statements, indent=switch_indent_level + 1)
                    self.content_list.append(
                        f"""\
{switch_indent_str}else"""
                    )
                    nest_level += 1

            if found_default:
                ## default case
                label_str = "default"
                self.content_list.append(
                    f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                )
                self._handle_list(found_default, indent=switch_indent_level + 1)
                self.content_list.append(
                    f"""\
{switch_indent_str}else
{switch_indent_str}    -[hidden]->
{switch_indent_str}endif"""
                )

            for _ in range(0, nest_level):
                nest_level -= 1
                switch_indent_level = indent + nest_level
                switch_indent_str = "    " * switch_indent_level
                self.content_list.append(
                    f"""\
{switch_indent_str}endif"""
                )

            ## switch end
            self.content_list.append(
                """\
}"""
            )
            return

        raise RuntimeError(f"unhandled statement type: {statement.type}")
