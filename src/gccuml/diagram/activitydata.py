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

from typing import List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ===========================================================


NODE_COLOR = "#fefece"
LAST_NODE_COLOR = "lightgreen"
UNSUPPORTED_COLOR = "orange"


## ===========================================================


FunctionArg = NamedTuple("FunctionArg", [("name", str), ("type", str)])


class ActivityData:
    pass


class StatementType(Enum):
    UNSUPPORTED = auto()
    NODE = auto()
    IF = auto()
    GOTO = auto()
    GOTOLABEL = auto()
    STOP = auto()


class Statement(ActivityData):
    def __init__(self, statement_name: str):
        super().__init__()
        self.name: str = statement_name
        self.color: str = None


class TypedStatement(Statement):
    """Container for function data to be presented on graph.

    Depending on 'type' it can be node, if or other language construct.
    """

    def __init__(self, statement_name: str, statement_type: StatementType = StatementType.NODE):
        super().__init__(statement_name)
        self.type: StatementType = statement_type
        self.items: List[Any] = []


class SwitchStatement(Statement):
    def __init__(self, statement_name: str):
        super().__init__(statement_name)
        self.items: List[Any] = []


class StatementList(ActivityData):

    def __init__(self):
        super().__init__()
        self.items: List[ActivityData] = []

    def append(self, item):
        self.items.append(item)


class LabeledCard(ActivityData):
    """Container for function data to be presented on graph.

    Item is presented as group/card.
    """

    def __init__(self, label: str = None):
        super().__init__()
        self.label = label
        self.subitems: List[ActivityData] = None
        self.has_return: bool = False

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


class LabeledGroup(ActivityData):
    """Container for function data to be presented on graph."""

    def __init__(self, label: str = None, subitems=None):
        super().__init__()
        self.label = label
        self.subitems: List[ActivityData] = subitems
        if self.subitems is None:
            self.subitems = []

    def append(self, item):
        self.subitems.append(item)


class SubNodeList(ActivityData):

    def __init__(self):
        super().__init__()
        self.subitems: List[ActivityData] = []

    def append(self, item):
        self.subitems.append(item)


class SubGraph(ActivityData):

    def __init__(self, label=None, items_list=None):
        super().__init__()
        self.label: str = label
        self.subitems: List[ActivityData] = items_list
        if self.subitems is None:
            self.subitems = []

    def append(self, item):
        self.subitems.append(item)
