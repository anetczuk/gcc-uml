# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Any

from typing import List, Dict

from showgraph.io import write_file
from gccuml.diagram import activitydata
from gccuml.diagram.activitydata import StatementType


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ===========================================================


class ActivityItem:

    @staticmethod
    def convert(data: Any):
        raise NotImplementedError("not implemented")

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


class Statement(ActivityItem):
    """Container for function data to be presented on graph.

    Depending on 'type' it can be
    """

    def __init__(self, statement_name: str = "", statement_type: StatementType = StatementType.NODE):
        super().__init__()
        self.name: str = statement_name
        self.type: StatementType = statement_type
        self.color: str = None
        self.items: List[Any] = []

    @staticmethod
    def convert(data: activitydata.Statement):
        item = Statement()
        item.name = data.name
        item.color = data.color
        if isinstance(data, activitydata.TypedStatement):
            item.type = data.type
            item.items = convert_list(data.items)
        elif isinstance(data, activitydata.Statement):
            item.type = StatementType.NODE
        return item

    def generate(self, indent) -> str:
        content_list = self._generate(indent)
        content = "\n".join(content_list)
        return content

    def _generate(self, indent) -> List[str]:
        indent_str = "    " * indent
        content_list = []

        if self.type == StatementType.UNSUPPORTED:
            node_color = convert_color_attribute(activitydata.UNSUPPORTED_COLOR)
            content_list.append(
                f"""\
{indent_str}{node_color}:{self.name};"""
            )
            content_list.append(
                f"""\
{indent_str}note right: not supported"""
            )
            return content_list

        if self.type == StatementType.NODE:
            node_color = convert_color_attribute(self.color)

            content_list.append(
                f"""\
{indent_str}{node_color}:{self.name};"""
            )
            return content_list

        if self.type == StatementType.STOP:
            node_color = convert_color_attribute(activitydata.LAST_NODE_COLOR)

            if self.name:
                content_list.append(
                    f"""\
{indent_str}{node_color}:{self.name};"""
                )
            content_list.append(
                f"""\
{indent_str}stop"""
            )
            return content_list

        if self.type == StatementType.GOTO:
            node_color = convert_color_attribute(activitydata.UNSUPPORTED_COLOR)
            label_value = "goto"
            if self.name:
                label_value = f"{label_value} {self.name}"
            content_list.append(
                f"""\
{indent_str}{node_color}:{label_value};"""
            )
            content_list.append(
                f"""\
{indent_str}note right: not supported"""
            )
            return content_list

        if self.type == StatementType.GOTOLABEL:
            node_color = convert_color_attribute(activitydata.UNSUPPORTED_COLOR)
            label_value = "label"
            if self.name:
                label_value = f"{label_value} {self.name}"
            content_list.append(
                f"""\
{indent_str}{node_color}:{label_value};"""
            )
            content_list.append(
                f"""\
{indent_str}note right: not supported"""
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

        raise RuntimeError(f"unhandled statement type: {self.type}")


class SwitchStatement(ActivityItem):

    def __init__(self, statement_name: str = ""):
        super().__init__()
        self.name: str = statement_name
        self.color: str = None
        self.items: List[Any] = []

    @staticmethod
    def convert(data: activitydata.SwitchStatement):
        item = SwitchStatement()
        item.name = data.name
        item.color = data.color
        item.items = convert_list(data.items)
        return item

    def generate(self, indent) -> str:
        # indent_str = "    " * indent

        items_num = len(self.items)
        if items_num < 1:
            # no cases
            return ""

        content_list: List[str] = []

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

        content = "\n".join(content_list)
        return content


class StatementList(ActivityItem):

    def __init__(self):
        super().__init__()
        self.items: List[ActivityItem] = []

    @staticmethod
    def convert(data: activitydata.StatementList):
        item = StatementList()
        item.items = convert_list(data.items)
        return item

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

    @staticmethod
    def convert(data: activitydata.LabeledCard):
        item = LabeledCard()
        item.label = data.label
        item.subitems = convert_list(data.subitems)
        return item

    def set_label(self, func_name: str, args_list: List[activitydata.FunctionArg], returntype: str):
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

    @staticmethod
    def convert(data: activitydata.LabeledGroup):
        item = LabeledGroup()
        item.label = data.label
        item.subitems = convert_list(data.subitems)
        return item

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

    @staticmethod
    def convert(_data: activitydata.SubNodeList):
        raise NotImplementedError("not implemented")
        # return None

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

    @staticmethod
    def convert(_data: activitydata.SubGraph):
        raise NotImplementedError("not implemented")
        # return None

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


def convert_color_attribute(node_color):
    if node_color is None:
        return ""
    if not node_color.startswith("#"):
        return f"#{node_color}"
    return node_color


## ===========================================================


CONVERT_DICT = {
    activitydata.SwitchStatement: SwitchStatement,
    activitydata.TypedStatement: Statement,
    activitydata.Statement: Statement,
    activitydata.StatementList: StatementList,
    activitydata.LabeledCard: LabeledCard,
    activitydata.LabeledGroup: LabeledGroup,
    activitydata.SubNodeList: SubNodeList,
    activitydata.SubGraph: SubGraph,
}


def convert_data(data: Any) -> Any:
    # if isinstance(data, ActivityItem):
    #     ## backward compatibility
    #     return data
    if isinstance(data, tuple):
        ## backward compatibility
        return convert_tuple(data)
    if isinstance(data, list):
        ## backward compatibility
        return convert_list(data)
    if isinstance(data, dict):
        ## backward compatibility
        return convert_dict(data)

    data_type = type(data)
    converter: Any = CONVERT_DICT.get(data_type)
    if converter is not None:
        # raise RuntimeError(f"unable to find converter for type {data_type}")
        converted = converter.convert(data)
        if converted is None:
            raise RuntimeError(f"unable to convert data type {data_type}")
        return converted

    # no conversion
    return data


def convert_tuple(data_tuple):
    ret_list = convert_list(data_tuple)
    return tuple(ret_list)


def convert_list(data_list: List[activitydata.ActivityData]) -> List[ActivityItem]:
    ret_list = []
    for data in data_list:
        converted = convert_data(data)
        ret_list.append(converted)
    return ret_list


def convert_dict(data_dict: Dict[str, activitydata.ActivityData]) -> Dict[str, ActivityItem]:
    ret_dict = {}
    for key, data in data_dict.items():
        converted = convert_data(data)
        ret_dict[key] = converted
    return ret_dict


## ===========================================================


## Generator for PlantUml activity diagrams
class ActivityDiagramGenerator:

    def __init__(self, data_dict: Dict[str, activitydata.ActivityData] = None):
        self.data: Dict[str, ActivityItem] = convert_dict(data_dict)
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
