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


FunctionArg = NamedTuple("FunctionArg", [("name", str), ("type", str)])


class ActivityItem:

    def generate(self, indent) -> str:
        raise NotImplementedError("not implemented")

    def _handle_list(self, items_list: List["ActivityItem"], indent=0) -> List[str]:
        content_list = []
        # stat: ActivityItem
        for sub_item in items_list:
            stat_content = sub_item.generate(indent)
            if stat_content:
                content_list.append(stat_content)
        return content_list


class StatementType(Enum):
    UNSUPPORTED = auto()
    NODE = auto()
    IF = auto()
    SWITCH = auto()
    GOTO = auto()
    GOTOLABEL = auto()
    STOP = auto()


class Statement(ActivityItem):
    """Container for function data to be presented on graph.

    Depending on 'type' it can be
    """

    def __init__(self, statement_name: str, statement_type: StatementType = StatementType.NODE):
        super().__init__()
        self.name: str = statement_name
        self.type: StatementType = statement_type
        self.color: str = None
        self.items: List[Any] = []

    def generate(self, indent) -> str:
        content_list = self._generate(indent)
        content = "\n".join(content_list)
        return content

    def _generate(self, indent) -> List[str]:
        indent_str = "    " * indent
        content_list = []

        if self.type == StatementType.UNSUPPORTED:
            content_list.append(
                f"""\
{indent_str}#orange:{self.name};"""
            )
            content_list.append(
                f"""\
{indent_str}note right: not supported"""
            )
            return content_list

        if self.type == StatementType.NODE:
            color = self.color
            if color is None:
                color = ""

            content_list.append(
                f"""\
{indent_str}{color}:{self.name};"""
            )
            return content_list

        if self.type == StatementType.STOP:
            if self.name:
                content_list.append(
                    f"""\
{indent_str}#lightgreen:{self.name};"""
                )
            content_list.append(
                f"""\
{indent_str}stop"""
            )
            return content_list

        if self.type == StatementType.GOTO:
            content_list.append(
                f"""\
{indent_str}goto {self.name}"""
            )
            return content_list

        if self.type == StatementType.GOTOLABEL:
            content_list.append(
                f"""\
{indent_str}label {self.name}"""
            )
            return content_list

        if self.type == StatementType.IF:
            items_len = len(self.items)
            if items_len != 2:
                raise RuntimeError(f"invalid IF node: required 2 items, got {items_len}")
            true_branch: List[ActivityItem] = self.items[0]
            false_branch: List[ActivityItem] = self.items[1]
            content_list.append(
                f"""\
{indent_str}if ({self.name} ?) then (true)"""
            )
            sub_content = self._handle_list(true_branch, indent=indent + 1)
            content_list.extend(sub_content)
            content_list.append(
                f"""\
{indent_str}else (false)"""
            )
            sub_content = self._handle_list(false_branch, indent=indent + 1)
            content_list.extend(sub_content)
            content_list.append(
                f"""\
{indent_str}endif"""
            )
            return content_list

        if self.type == StatementType.SWITCH:
            items_num = len(self.items)
            if items_num < 1:
                # no cases
                return content_list

            ## switch start
            content_list.append(
                f"""
partition "switch:\\n{self.name}" {{"""
            )

            nest_level = 0
            found_default = None

            for case_item in self.items:
                case_value = case_item[0]
                case_fallthrough = case_item[1]
                case_statements = case_item[2]

                switch_indent_level = indent + nest_level
                switch_indent_str = "    " * switch_indent_level

                content_list.append(
                    f"""\
{switch_indent_str}' case: {case_value} fallthrough: {case_fallthrough}"""
                )

                if case_value is None:
                    found_default = case_statements
                    continue

                label_str = f"{case_value} ?"

                if case_fallthrough:
                    ## fallthrough
                    content_list.append(
                        f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                    )
                    sub_content = self._handle_list(case_statements, indent=switch_indent_level + 1)
                    content_list.extend(sub_content)
                    content_list.append(
                        f"""\
{switch_indent_str}endif"""
                    )
                #                     content_list.append(
                #                         f"""\
                # {switch_indent_str}note right: [fallthrough]"""
                #                     )
                else:
                    ## normal or default
                    content_list.append(
                        f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                    )
                    sub_content = self._handle_list(case_statements, indent=switch_indent_level + 1)
                    content_list.extend(sub_content)
                    content_list.append(
                        f"""\
{switch_indent_str}else"""
                    )
                    nest_level += 1

            if found_default:
                ## default case
                label_str = "default"
                content_list.append(
                    f"""\
{switch_indent_str}if ( {label_str} ) then (yes)"""
                )
                sub_content = self._handle_list(found_default, indent=switch_indent_level + 1)
                content_list.extend(sub_content)
                content_list.append(
                    f"""\
{switch_indent_str}else
{switch_indent_str}    -[hidden]->
{switch_indent_str}endif"""
                )

            for _ in range(0, nest_level):
                nest_level -= 1
                switch_indent_level = indent + nest_level
                switch_indent_str = "    " * switch_indent_level
                content_list.append(
                    f"""\
{switch_indent_str}endif"""
                )

            ## switch end
            content_list.append(
                """\
}"""
            )
            return content_list

        raise RuntimeError(f"unhandled statement type: {self.type}")


class StatementList(ActivityItem):

    def __init__(self):
        super().__init__()
        self.items: List[ActivityItem] = []

    def append(self, item):
        self.items.append(item)

    def generate(self, indent) -> str:
        sub_content = self._handle_list(self.items, indent)
        content = "\n".join(sub_content)
        return content


class LabeledCard(ActivityItem):
    """Container for function data to be presented on graph.

    Item is presented as group/card.
    """

    def __init__(self, label: str = None):
        super().__init__()
        self.label = label
        self.subitems: List[ActivityItem] = None

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

    def generate(self, indent) -> str:
        indent_str = "    " * indent
        content_list = []

        label = self.label
        label = label.replace('"', "'")  ## workaround for PlantUML problem

        content_list.append(
            f"""\
{indent_str}card "{label}" {{"""
        )
        #         content_list.append(
        #             f"""\
        # {indent_str}card "{self.label}" {{
        # {indent_str}    start"""
        #         )

        sub_content = self._handle_list(self.subitems, indent + 1)
        content_list.extend(sub_content)

        content_list.append(
            f"""\
{indent_str}    -[hidden]->
{indent_str}}}
"""
        )
        content = "\n".join(content_list)
        return content


class LabeledGroup(ActivityItem):
    """Container for function data to be presented on graph."""

    def __init__(self, label: str = None, subitems=None):
        super().__init__()
        self.label = label
        self.subitems: List[ActivityItem] = subitems
        if self.subitems is None:
            self.subitems = []

    def append(self, item):
        self.subitems.append(item)

    def generate(self, indent) -> str:
        indent_str = "    " * indent
        content_list = []

        content_list.append(
            f"""\
{indent_str}group {self.label}"""
        )

        sub_content = self._handle_list(self.subitems, indent + 1)
        content_list.extend(sub_content)

        content_list.append(
            f"""\
{indent_str}end group
"""
        )
        content = "\n".join(content_list)
        return content


class SubNodeList(ActivityItem):

    def __init__(self):
        super().__init__()
        self.subitems: List[ActivityItem] = []

    def append(self, item):
        self.subitems.append(item)

    def generate(self, indent) -> str:
        indent_str = "    " * indent
        content_list = []
        content_list.append(
            f"""\
{indent_str}:"""
        )
        sub_content = self._handle_list(self.subitems, indent + 1)
        content_list.extend(sub_content)
        content_list.append(
            f"""\
{indent_str};"""
        )
        content = "\n".join(content_list)
        return content


## does not work is subgraphs are nested
class SubGraph(ActivityItem):

    def __init__(self, label=None, items_list=None):
        super().__init__()
        self.label: str = label
        self.subitems: List[ActivityItem] = items_list
        if self.subitems is None:
            self.subitems = []

    def append(self, item):
        self.subitems.append(item)

    def generate(self, indent) -> str:
        indent_str = "    " * indent
        content_list = []
        content_list.append(
            f"""\
{indent_str}{{{{
{indent_str}    mainframe {self.label}"""
        )

        for subitem in self.subitems:
            content_list.append(f"{indent_str}    -[hidden]->")
            item_content = subitem.generate(indent + 1)
            content_list.append(item_content)

        content_list.append(
            f"""\
{indent_str}}}}}"""
        )

        content = "\n".join(content_list)
        return content


## ===========================================================


## Generator for PlantUml activity diagrams
class ActivityDiagramGenerator:

    def __init__(self, data_dict=None):
        self.data: Dict[str, ActivityItem] = data_dict
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
        for stat in items_list:
            item_content = stat.generate(0)
            self.content_list.append(item_content)

        ##
        ## close diagram
        ##
        self.content_list.append("\n@enduml\n")
        content = "\n".join(self.content_list)

        # print(f"\ndiagram:\n{content}")

        _LOGGER.info("writing output to file %s", out_path)
        write_file(out_path, content)
