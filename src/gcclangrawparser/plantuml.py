# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
import itertools
import math
import hashlib
from enum import Enum, auto
from typing import NamedTuple, Tuple

from typing import Set, List, Dict

from showgraph.io import write_file, read_list

from gcclangrawparser.seqgraph import SequenceGraph, SeqItems, MsgData, DiagramData, NodeData, NotesContainer


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


BG_COLORS_PATH = os.path.join(SCRIPT_DIR, "plantuml_bg_colors.txt")
BG_COLORS_LIST = read_list(BG_COLORS_PATH)


## ===========================================================


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
    ClassField = NamedTuple("ClassField", [("name", str), ("type", str), ("access", str)])
    ClassMethod = NamedTuple(
        "ClassMethod", [("name", str), ("type", str), ("modifier", str), ("access", str), ("args", List[FunctionArg])]
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
                field_name, field_type, field_access = field_item
                access_mark = self.FIELD_ACCESS_DICT.get(field_access)
                if access_mark is None:
                    _LOGGER.error("unable to get access mark for access value: '%s'", field_access)
                    access_mark = ""
                content_list.append(f"""    {{field}} {access_mark} {field_type} {field_name}""")

            for method_item in class_data.methods:
                method_name, method_type, method_mod, method_access, method_args = method_item
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

                method_mod_suffix = []
                if "const" in method_mod:
                    method_mod_suffix.append("const")
                if "purevirt" in method_mod:
                    method_mod_suffix.append("=0")
                if "default" in method_mod:
                    method_mod_suffix.append("=default")
                method_mod_suffix = " ".join(method_mod_suffix)

                content_list.append(
                    f"""    {{method}} {access_mark}{method_mod_prefix} {method_type}"""
                    f""" {method_name}({args_string}) {method_mod_suffix}"""
                )

            content_list.append("}")

        content_list.append("")

        for class_data in self.classes.values():
            from_class = class_data.name
            from_id = name_dict[from_class]
            for base in class_data.bases:
                to_id = name_dict[base.name]
                content_list.append(f"""' {from_class} --|> {base.name}""")
                content_list.append(f"""{from_id} --|> {to_id}: "{base.access}\"""")

        content_list.append("\n@enduml\n")
        content = "\n".join(content_list)

        print(f"\ndiagram:\n{content}")

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


## ===========================================================


def generate_diagram(diagram_data: DiagramData, out_path):
    """Generate PlantUML diagram and store to file."""
    params = diagram_data.params
    genrator = SequenceDiagramGenerator(diagram_data, params)
    genrator.generate(out_path)


##
class SequenceDiagramGenerator:

    def __init__(self, diagram_data: DiagramData, params: dict = None):
        self.diagram_data = diagram_data

        self.name_dict: Dict[str, str] = {}
        self.params_dict = params
        if self.params_dict is None:
            self.params_dict = {}

        self.actors_order: List[str] = []

    def generate(self, out_path):
        seq_graph: SequenceGraph = self.diagram_data.seq_diagram

        call_len = seq_graph.size()
        if call_len < 1:
            content = """\
@startuml
@enduml
"""
            write_file(out_path, content)
            return

        content = """\
@startuml

skinparam backgroundColor #FEFEFE

"""

        graph_actors: Set[str] = seq_graph.actors()
        labels_dict = self.calculate_labels_dict(seq_graph)
        self.actors_order = calculate_actors_optimized_order(graph_actors, labels_dict)

        ## add actors
        for actor_name in self.actors_order:
            node_data: NodeData = self.diagram_data.getNodeByName(actor_name)
            if node_data is None:
                continue

            item_id = self._get_item_id(actor_name)
            item_path = os.path.join(self.diagram_data.root_subdir, node_data.suburl)

            actor_bg_color = node_data.params.get("bg_color", None)
            if actor_bg_color is None and BG_COLORS_LIST:
                ## BG_COLORS
                item_hash = hashlib.sha256(item_id.encode("utf-8")).hexdigest()
                bg_color_index = int(item_hash, 16) % len(BG_COLORS_LIST)
                actor_bg_color = BG_COLORS_LIST[bg_color_index]

            if actor_bg_color:
                content += f"""box #{actor_bg_color}\n"""
                ## content += f"""'bg color: {bg_color}\n"""
                content += f"""    participant "{actor_name}" as {item_id} [[{item_path}]]\n"""
                content += "end box\n"
            else:
                content += f"""participant "{actor_name}" as {item_id} [[{item_path}]]\n"""

        content += "\n"

        detect_loops = seq_graph.loopsFound()

        ## add calls
        loops = seq_graph.getLoops()
        for seq in loops:
            use_msg_loop = seq.repeats > 1 and detect_loops
            indent = ""

            if use_msg_loop:
                content += f"""\nloop {seq.repeats} times\n"""
                indent = "    "

            loop_content = self.generate_loop(seq, indent)

            content += loop_content
            if use_msg_loop:
                content += "end\n"

        content += "\n@enduml\n"

        write_file(out_path, content)

    def generate_loop(self, seq: SeqItems, loop_indent):
        content = ""
        group_subs = self.params_dict.get("group_subs", False)

        calls: List[MsgData] = seq.items
        ## item: MsgData
        for msg_data in calls:
            receivers = sorted(msg_data.subs, reverse=True)

            message_url = None
            if msg_data.is_message_set():
                message_url = msg_data.get_prop("url", None)
            if message_url is not None:
                message_url = os.path.join(self.diagram_data.root_subdir, message_url)

            ## topic url: out/topics/_turtle1_cmd_vel.html
            call_label = self.calculate_label(msg_data, message_url)
            indent = ""

            use_subs_group = len(receivers) > 1 and group_subs
            if use_subs_group:
                ## grouping topic subscribers
                content += f"""{loop_indent}group {call_label}\n"""
                call_label = ""
                indent = "    "

            pub_id = self._get_item_id(msg_data.pub)
            for rec in receivers:
                rec_id = self._get_item_id(rec)
                content += f"""{loop_indent}{indent}{pub_id} o-> {rec_id} : {call_label}\n"""
                if call_label:
                    notes_content = convert_notes(msg_data.notes_data)
                    if notes_content is not None:
                        bg_color = msg_data.notes_data.bg_color
                        if bg_color is None:
                            bg_color = ""
                        elif not bg_color.startswith("#"):
                            bg_color = "#" + bg_color
                        content += f"""\
note left {bg_color}
{notes_content}
end note
"""
                call_label = ""  ## clear label after first item

            if use_subs_group:
                content += f"""{loop_indent}end\n"""

        return content

    def call_time(self, item: MsgData):
        timestamp_dt = item.get_timestamp_date_time()
        timestamp_string = timestamp_dt.strftime("%H:%M:%S.%f")
        return timestamp_string

    def calculate_label(self, item: MsgData, url=None):
        ret_content = ""

        timestamp_string = self.call_time(item)
        if url is None:
            ret_content = f"""**{timestamp_string}**: """
        else:
            ## {message data} is tooltip of hyperlink
            plantuml_url = generate_url(url, timestamp_string, "message data")
            ret_content = f"""**{plantuml_url}**: """

        labels_list = []
        url_list = self.diagram_data.get_topics_urls(item.topics)
        for topic_name, topic_url in url_list:
            if topic_url:
                plantuml_url = generate_url(topic_url, topic_name, "topic data")
                labels_list.append(plantuml_url)
            else:
                labels_list.append(topic_name)
        ret_content += " | ".join(labels_list)
        return ret_content

    def calculate_labels_dict(self, seq_graph: SequenceGraph):
        labels_dict = {}
        loops: List[SeqItems] = seq_graph.get_loops()
        for seq in loops:
            calls: List[MsgData] = seq.items
            for call in calls:
                labels_dict[call] = self.calculate_label(call)
        return labels_dict

    def _get_item_id(self, item_name):
        proper = self.name_dict.get(item_name, None)
        if proper is not None:
            return proper
        name = item_name.replace("/", "_")
        self.name_dict[item_name] = name
        return name

    def _is_to_right(self, from_actor, to_actor):
        from_index = self.actors_order.index(from_actor)
        to_index = self.actors_order.index(to_actor)
        return from_index < to_index


## ========================================================================


def convert_notes(notes_data: NotesContainer):
    if notes_data is None:
        return None
    content_list = []
    for notes_list in notes_data:
        content_line = []
        for note in notes_list:
            note_type = note["type"]
            note_msg = note["msg"]
            if note_type == NotesContainer.NoteType.INFO.name:
                content_line.append(note_msg)
            elif note_type == NotesContainer.NoteType.ERROR.name:
                msg = format_note_error(note_msg)
                content_line.append(msg)
            else:
                _LOGGER.warning("unhandled note type: %s", note_type)
                content_line.append(note_msg)
        content = " ".join(content_line)
        content_list.append(content)
    return "\n".join(content_list)


def format_note_error(message: str):
    return f"""<b><back:salmon>{message}</back></b>"""


def generate_url(url, label, tooltip):
    return f"""[[{url} {{{tooltip}}} {label}]]"""


def calculate_actors_optimized_order(graph_actors, labels_dict) -> List[str]:
    #     return sorted( graph_actors )

    distance_dict = {}
    for item, label in labels_dict.items():
        pub = item.pub
        receivers = sorted(item.subs, reverse=True)
        if len(receivers) < 1:
            ## set non-empty label for first subscriber
            continue
        key = tuple(sorted([pub, receivers[0]]))
        distance_dict[key] = len(label)

    sorted_actors = list(sorted(graph_actors))
    sorted_width = calculate_width(sorted_actors, distance_dict)
    best_order = sorted_actors
    best_width = sorted_width

    a_size = len(sorted_actors)

    perm_size = math.factorial(a_size)
    if perm_size > 10000:
        _LOGGER.warning("unable to calculate best order: %s %s %s", len(labels_dict), a_size, perm_size)
        return sorted_actors

    _LOGGER.info("calculating best order: %s %s", len(labels_dict), a_size)

    for curr_list in itertools.permutations(sorted_actors, a_size):
        curr_width = calculate_width(curr_list, distance_dict)
        if curr_width < best_width:
            best_order = list(curr_list)
            best_width = curr_width

    _LOGGER.info("best order: %s %s %s", best_order, best_width, sorted_width)
    return best_order


#     found_best = True
#     while found_best:
#         found_best = False
#         for actor in sorted_actors:
#             index        = best_order.index( actor )
#             combinations = calculate_combinations( best_order, index )
#             for curr_list in combinations:
#                 curr_width = calculate_width( curr_list, distance_dict )
#                 if curr_width < best_width:
#                     best_order = curr_list
#                     best_width = curr_width
#                     found_best = True
#     print( "best order:", best_order, best_width, sorted_width )
#     return best_order


def calculate_width(actors_list, distance_dict):
    a_size = len(actors_list)
    index_distance = [0.0] * a_size
    for i in range(1, a_size):
        curr_actor = actors_list[i]
        max_dist = 0.0
        for j in range(i - 1, -1, -1):
            prev_actor = actors_list[j]
            key = tuple(sorted([prev_actor, curr_actor]))
            dist = distance_dict.get(key, 0.0)
            curr_dist = index_distance[j] + dist
            max_dist = max(max_dist, curr_dist)
        index_distance[i] = max_dist
    return index_distance[a_size - 1]


def calculate_combinations(actors_list, index):
    ret_list = []
    list_size = len(actors_list)
    item = actors_list[index]
    reduced_list = actors_list.copy()
    del reduced_list[index]
    for i in range(0, list_size):
        curr_actor = reduced_list.copy()
        curr_actor.insert(i, item)
        ret_list.append(curr_actor)
    return ret_list


def convert_time_index(index_value):
    time_unit = "ms"
    time_value = index_value / 1000000  ## in milliseconds
    if time_value > 10000.0:
        time_value = time_value / 1000
        time_unit = "s"
    return (time_value, time_unit)
