# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from enum import Enum, auto
from typing import NamedTuple, Tuple
from typing import List, Dict
from dataclasses import dataclass

from showgraph.io import write_file


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ===========================================================


## Generator for PlantUml class diagrams
class ClassDiagramGenerator:

    CLASS_SPOT_COLOR = "#add1b2"

    class ClassType(Enum):
        """Predefined struct type."""

        CLASS = auto()
        TEMPLATE = auto()

    class ClassData:
        """Container for class data to be presented on graph."""

        def __init__(self, name=None):
            self.type: ClassDiagramGenerator.ClassType = None  # predefined spot if not explicit
            self.spot: Tuple[str, str] | str = None  # string and color (color name or #RGB)

            self.name: str = name
            self.bases: List[ClassDiagramGenerator.ClassBase] = []
            self.fields: List[ClassDiagramGenerator.ClassField] = []
            self.methods: List[ClassDiagramGenerator.ClassMethod] = []
            self.generics: List[str] = []

    FunctionArg = NamedTuple("FunctionArg", [("name", str), ("type", str)])
    ClassBase = NamedTuple("ClassBase", [("name", str), ("access", str)])

    
    @dataclass
    class ClassField:
        name: str
        type: str
        access: str
        static: bool


    ClassMethod = NamedTuple(
        "ClassMethod",
        [
            ("name", str),
            ("type", str),
            ("modifier", str),
            ("access", str),
            ("args", List[FunctionArg]),
            ("static", bool),
        ],
    )
    Connection = NamedTuple("Connection", [("from_class", str), ("to_class", str), ("label", str)])

    FIELD_ACCESS_DICT = {"private": "-", "protected": "#", "package private": "~", "public": "+"}

    def __init__(self, class_data_dict=None):
        self.classes: Dict[str, ClassDiagramGenerator.ClassData] = class_data_dict
        if self.classes is None:
            self.classes = {}

    def add_class(self, name: str):
        self.classes[name] = self.ClassData(name)

    def add_base(self, class_name, base: ClassBase):
        class_data: ClassDiagramGenerator.ClassData = self.classes[class_name]
        class_data.bases.append(base)

    def add_class_field(self, class_name, field_data: ClassField):
        class_data: ClassDiagramGenerator.ClassData = self.classes[class_name]
        class_data.fields.append(field_data)

    def add_class_method(self, class_name, method_data: ClassMethod):
        class_data: ClassDiagramGenerator.ClassData = self.classes[class_name]
        class_data.methods.append(method_data)

    def generate(self, out_path):
        if not self.classes:
            ## empty data
            content = """\
@startuml
@enduml
"""
            _LOGGER.info("writing output to file %s", out_path)
            write_file(out_path, content)
            return

        # generate
        content_list = []
        content_list.append(
            """\
@startuml
"""
        )

        counter = 0
        name_dict = {}

        ##
        ## add nodes
        ##
        for class_data in self.classes.values():
            actor = class_data.name
            actor_id = f"item_{counter}"
            counter += 1
            name_dict[actor] = actor_id

            struct_spot = self._get_spot_value(class_data)
            if struct_spot:
                struct_spot = f"{struct_spot} "

            gen_string = ""
            if class_data.generics:
                gen_string = ", ".join(class_data.generics)
                gen_string = f"<{gen_string}> "

            content_list.append(f"""class "{actor}" as {actor_id} {gen_string}{struct_spot}{{""")

            for field_item in class_data.fields:
                field_name = field_item.name
                field_type = field_item.type
                field_access = field_item.access
                field_static = field_item.static
                access_mark = self.FIELD_ACCESS_DICT.get(field_access)
                if access_mark is None:
                    _LOGGER.error("unable to get access mark for access value: '%s'", field_access)
                    access_mark = ""

                static_marker = ""
                if field_static:
                    # in UML static field is marked as underscored
                    static_marker = "{static} "

                content_list.append(f"""    {{field}} {static_marker}{access_mark} {field_type} {field_name}""")

            for method_item in class_data.methods:
                method_name, method_type, method_mod, method_access, method_args, method_static = method_item
                access_mark = self.FIELD_ACCESS_DICT.get(method_access)
                if access_mark is None:
                    _LOGGER.error("unable to get access mark for access value: '%s'", method_access)
                    access_mark = ""

                args_list = []
                for arg_item in method_args:
                    if arg_item.name:
                        args_list.append(f"{arg_item.type} {arg_item.name}")
                    else:
                        args_list.append(f"{arg_item.type} /*anonym*/")
                        # args_list.append(arg_item.type)
                args_string = ", ".join(args_list)

                method_mod_prefix = ""
                if "virtual" in method_mod:
                    method_mod_prefix = "virt"

                abstract_mark = ""
                method_mod_suffix = []
                if "const" in method_mod:
                    method_mod_suffix.append("const")
                if "purevirt" in method_mod:
                    method_mod_suffix.append("=0")
                    abstract_mark = "{abstract} "
                if "default" in method_mod:
                    method_mod_suffix.append("=default")
                method_mod_suffix = " ".join(method_mod_suffix)

                static_marker = ""
                if method_static:
                    # in UML static method is marked as underscored
                    static_marker = "{static} "

                content_list.append(
                    f"""    {{method}} {static_marker}{abstract_mark}{access_mark}{method_mod_prefix} {method_type}"""
                    f""" {method_name}({args_string}) {method_mod_suffix}"""
                )

            content_list.append("}")

        content_list.append("")

        ##
        ## add connections
        ##
        for class_data in self.classes.values():
            from_class = class_data.name
            from_id = name_dict[from_class]
            for base in class_data.bases:
                to_id = name_dict.get(base.name)
                if to_id is None:
                    _LOGGER.error("unable to get id from class %s", base.name)
                    continue
                if base.access:
                    content_list.append(f"""' {from_class} --|> {base.name}""")
                    content_list.append(f"""{from_id} --|> {to_id}: "{base.access}\"""")
                else:
                    content_list.append(f"""' {from_class} ..> {base.name}""")
                    content_list.append(f"""{from_id} ..> {to_id}""")

        ##
        ## close diagram
        ##
        content_list.append("\n@enduml\n")
        content = "\n".join(content_list)

        # print(f"\ndiagram:\n{content}")

        _LOGGER.info("writing output to file %s", out_path)
        write_file(out_path, content)

    def _get_spot_value(self, class_data: "ClassDiagramGenerator.ClassData"):
        if class_data.spot:
            if isinstance(class_data.spot, str):
                return class_data.spot
            spot_string = class_data.spot[0]
            spot_string = spot_string[0]  # get single character
            spot_color = class_data.spot[1]
            if not spot_color:
                spot_color = self.CLASS_SPOT_COLOR
            return f"<<({spot_string},{spot_color})>>"

        if class_data.type == ClassDiagramGenerator.ClassType.CLASS:
            # default style
            return ""

        if class_data.type == ClassDiagramGenerator.ClassType.TEMPLATE:
            return "<<T,#FF7700>>"

        return ""
