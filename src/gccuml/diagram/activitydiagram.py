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


class FuncStatType(Enum):
    NODE = auto()
    IF = auto()
    SWITCH = auto()
    STOP = auto()


class FuncStatement:
    """Container for function data to be presented on graph."""

    def __init__(self, statement_name: str, statement_type: FuncStatType):
        self.name: str = statement_name
        self.type: FuncStatType = statement_type
        self.color: str = None
        self.items: List[Any] = []


FunctionArg = NamedTuple("FunctionArg", [("name", str), ("type", str)])


class FuncData:
    """Container for function data to be presented on graph."""

    def __init__(self, name):
        self.name: str = name
        self.args: List[FunctionArg] = []
        self.returntype: str = None
        self.statements = None


## ===========================================================


## Generator for PlantUml activity diagrams
class ActivityDiagramGenerator:

    def __init__(self, data_dict=None):
        self.data: Dict[str, FuncData] = data_dict
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

        # func_data: FuncData
        for func_data in self.data.values():
            func_name = func_data.name

            args_list = []
            for arg_item in func_data.args:
                if arg_item.name:
                    args_list.append(f"{arg_item.type} {arg_item.name}")
                else:
                    args_list.append(f"{arg_item.type} /*anonym*/")
                    # args_list.append(arg_item.type)
            args_string = ", ".join(args_list)

            ret_str = func_data.returntype

            self.content_list.append(
                f"""\
card "{func_name}({args_string}) -> {ret_str}" {{
    start"""
            )

            func_statements = func_data.statements
            self._handle_statement_list(func_statements)

            self.content_list.append(
                """\
}
"""
            )

        ##
        ## close diagram
        ##
        self.content_list.append("\n@enduml\n")
        content = "\n".join(self.content_list)

        # print(f"\ndiagram:\n{content}")

        _LOGGER.info("writing output to file %s", out_path)
        write_file(out_path, content)

    def _handle_statement_list(self, statement_list, indent=1):
        indent_str = "    " * indent
        for stat in statement_list:
            if stat.type == FuncStatType.NODE:
                color = stat.color
                if color is None:
                    color = ""

                self.content_list.append(
                    f"""\
{indent_str}{color}:{stat.name};"""
                )
                continue

            if stat.type == FuncStatType.STOP:
                if stat.name:
                    self.content_list.append(
                        f"""\
{indent_str}#lightgreen:{stat.name};"""
                    )
                self.content_list.append(
                    f"""\
{indent_str}stop"""
                )
                continue

            if stat.type == FuncStatType.IF:
                items_len = len(stat.items)
                if items_len != 2:
                    raise RuntimeError(f"invalid IF node: required 2 items, got {items_len}")
                true_branch = stat.items[0]
                false_branch = stat.items[1]
                self.content_list.append(
                    f"""\
{indent_str}if ({stat.name} ?) then (true)"""
                )
                self._handle_statement_list(true_branch, indent=indent + 1)
                self.content_list.append(
                    f"""\
{indent_str}else (false)"""
                )
                self._handle_statement_list(false_branch, indent=indent + 1)
                self.content_list.append(
                    f"""\
{indent_str}endif"""
                )
                continue

            if stat.type == FuncStatType.SWITCH:
                items_num = len(stat.items)
                if items_num < 1:
                    # no cases
                    continue

                ## switch start
                self.content_list.append(
                    f"""
partition "switch:\\n{stat.name}" {{"""
                )

                nest_level = 0
                found_default = None

                for case_item in stat.items:
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
                        self._handle_statement_list(case_statements, indent=switch_indent_level + 1)
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
                        self._handle_statement_list(case_statements, indent=switch_indent_level + 1)
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
                    self._handle_statement_list(found_default, indent=switch_indent_level + 1)
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

                continue

            raise RuntimeError(f"unhandled statement type: {stat.type}")
