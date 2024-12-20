# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
import copy
import datetime

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Dict, Any, Set

# from pympler import asizeof


_LOGGER = logging.getLogger(__name__)


## ========================================================================


class NotesContainer:

    @unique
    class NoteType(Enum):
        """Type of note."""

        INFO = "INFO"
        ERROR = "ERROR"

    def __init__(self, topics=None, bg_color: str = None):
        self.bg_color: str = bg_color
        self.topics = topics
        self._notes_lines: List[List[Any]] = []

    ## list interface
    def __len__(self):
        return len(self._notes_lines)

    ## list interface
    def __getitem__(self, item):
        return self._notes_lines[item]

    ## list interface
    def __iter__(self):
        return self._notes_lines.__iter__()

    @property
    def notes_lines(self):
        return self._notes_lines

    @notes_lines.setter
    def notes_lines(self, value):
        if isinstance(value, str):
            container = NotesContainer()
            container.add_info(value)
            value = container.notes_lines
        self._notes_lines = value

    def get_error_notes(self) -> List[Any]:
        ret_list = []
        for notes_line in self._notes_lines:
            for note in notes_line:
                if note["type"] == self.NoteType.ERROR.name:
                    ret_list.append(note)
        return ret_list

    def add_new_line(self):
        self._notes_lines.append([])

    def add_info(self, message, new_line=False):
        if new_line:
            self.add_new_line()
        if len(self._notes_lines) < 1:
            self.add_new_line()
        last_line: List[Any] = self._notes_lines[-1]
        last_line.append({"type": self.NoteType.INFO.name, "msg": message})

    def add_info_enum(self, label, value, enum_name):
        if enum_name is not None:
            self.add_info(f"{label} {value} ({enum_name})")
        else:
            self.add_info(f"{label} {value}")
            self.add_error("unknown enum")

    def add_error(self, message, new_line=False):
        if new_line:
            self.add_new_line()
        if len(self._notes_lines) < 1:
            self.add_new_line()
        last_line: List[Any] = self._notes_lines[-1]
        last_line.append({"type": self.NoteType.ERROR.name, "msg": message})


##
class MsgData:

    def __init__(self, msg_index, pub: str, subs: Set[str], index: int, timestamp_abs, topics: Set[str]):
        self.index = msg_index
        self.pub = pub  ## publisher node
        self.subs = subs  ## subscriber nodes
        self.timestamp_rel = index
        self.timestamp_abs = timestamp_abs
        self.topics: Set[str] = topics

        self.msgtype = None
        self.msgdef = None
        self.msgdata = None

        self.notes_data: NotesContainer = None

        self.props: Dict[str, Any] = {}

    def copy(self):
        return copy.deepcopy(self)

    def mem_size(self):
        return 0
        # return asizeof.asizeof( self )

    def mem_msg_size(self):
        return 0
        # return asizeof.asizeof( self.msgdata )

    def set_message_data(self, msgtype, msgdef, msgdata):
        self.msgtype = msgtype
        self.msgdef = msgdef
        self.msgdata = msgdata

    def clear_messagea_data(self):
        self.msgtype = None
        self.msgdef = None
        self.msgdata = None

    ## if topic is excluded, then message data will be not set
    def is_message_set(self):
        if self.msgtype is None:
            return False
        if self.msgdef is None:
            return False
        if self.msgdata is None:
            return False
        return True

    def get_prop(self, key, def_value=None):
        return self.props.get(key, def_value)

    def set_prop(self, key, value):
        self.props[key] = value

    def get_actors(self):
        ret_set = set()
        ret_set.add(self.pub)
        ret_set.update(self.subs)
        return ret_set

    def have_actor(self, actor):
        if self.pub == actor:
            return True
        if actor in self.subs:
            return True
        return False

    def have_label(self, topic):
        return topic in self.topics

    def same_actors(self, other_item: "MsgData"):
        if self.pub != other_item.pub:
            return False
        if self.subs != other_item.subs:
            return False
        return True

    def same_labels(self, other_item: "MsgData"):
        return self.topics == other_item.topics

    def add_labels(self, topics: Set[str]):
        self.topics = self.topics.union(topics)

    def hash_value(self):
        string_list = []
        string_list.append(self.pub)
        string_list.extend(self.subs)
        string_list.extend(self.topics)
        return hash(tuple(string_list))

    def get_timestamp_date_time(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.timestamp_abs / 1000000000)


##
class SeqItems:

    def __init__(self, items, repeat=1):
        self.items: List[MsgData] = items
        self.repeats: int = repeat
        if repeat > 1:
            for item in self.items:
                item.clearMessageaData()

    def size(self):
        return len(self.items)


## =============================================================


##
class SequenceGraph:

    def __init__(self):
        self.callings: List[MsgData] = []
        self.loops: List[SeqItems] = []

    def size(self):
        return len(self.callings)

    def items_num(self):
        if len(self.loops) < 1:
            return len(self.callings)
        counter = 0
        for seq in self.loops:
            counter += seq.size()
        return counter

    def get_loops(self) -> List[SeqItems]:
        if len(self.loops) < 1:
            self.loops.append(SeqItems(self.callings))
        return self.loops

    def loops_found(self):
        for loop in self.loops:
            if loop.repeats > 1:
                return True
        return False

    def actors(self) -> Set[str]:
        ret_set = set()
        for calls in self.callings:
            ret_set.add(calls.pub)
            ret_set.update(calls.subs)
        return ret_set

    def messages(self, set_only=True) -> List[MsgData]:
        ret_list = []
        ## loop: List[ SeqItems ]
        for loop in self.get_loops():
            if loop.repeats > 1:
                pass
            ## item: List[ MsgData ]
            for item in loop.items:
                if set_only and item.is_message_set() is False:
                    continue
                ret_list.append(item)
        return ret_list

    def add_call(self, msg_index, publisher, subscriber, index, timestamp, topic) -> MsgData:
        item = MsgData(
            msg_index,
            publisher,
            set(
                subscriber,
            ),
            index,
            timestamp,
            set([topic]),
        )
        self.callings.append(item)
        return item

    def add_call_subs(self, msg_index, publisher, subscribers_list, index, timestamp, topic) -> MsgData:
        item = MsgData(msg_index, publisher, set(subscribers_list), index, timestamp, set([topic]))
        self.callings.append(item)
        return item

    def process(self, params: dict = None):
        if params is None:
            params = {}

        if params.get("group_calls", False):
            self.group_topics()

        if params.get("group_topics", False):
            self.group_calls()

        if params.get("detect_loops", False):
            self.zip_seqs()

    def group_calls(self):
        call_len = len(self.callings)
        if call_len < 2:
            return self.callings
        groups = []
        prev_call = self.callings[0]
        for i in range(1, call_len):
            call = self.callings[i]
            if prev_call.sameActors(call):
                ## same pub and subs
                prev_call.addLabels(call.topics)
                prev_call.clearMessageaData()
                continue
            groups.append(prev_call)
            prev_call = call
        groups.append(prev_call)
        self.callings = groups
        return self.callings

    def group_topics(self):
        call_len = len(self.callings)
        if call_len < 2:
            return self.callings
        groups = []
        prev_call = self.callings[0]
        for i in range(1, call_len):
            call = self.callings[i]
            if prev_call.sameActors(call) and prev_call.sameLabels(call):
                prev_call.clearMessageaData()
                continue
            groups.append(prev_call)
            prev_call = call
        groups.append(prev_call)
        self.callings = groups
        return self.callings

    def zip_seqs(self):
        improved = True
        curr_loops: List[SeqItems] = self.get_loops()
        while improved:
            improved = False
            new_loops: List[SeqItems] = []
            for items_seq in curr_loops:
                if items_seq.repeats > 1:
                    new_loops.append(items_seq)
                    continue
                callings = items_seq.items
                seq_detector = SequenceDetector(callings, lambda item: item.hashValue())
                best_seq = seq_detector.detect()
                seq_gain = calculate_seq_gain(best_seq)
                if seq_gain < 2:
                    new_loops.append(items_seq)
                    continue

                _LOGGER.info("best loop detected: %s", best_seq)
                improved = True
                start_index = best_seq[0]
                next_index = best_seq[0] + best_seq[1]
                after_index = best_seq[0] + best_seq[1] * best_seq[2]

                prev = callings[:start_index]
                if len(prev) > 0:
                    new_loops.append(SeqItems(prev))

                repeat = callings[start_index:next_index]
                new_loops.append(SeqItems(repeat, best_seq[2]))

                after = callings[after_index:]
                if len(after) > 0:
                    new_loops.append(SeqItems(after))
            curr_loops = new_loops
        self.loops = curr_loops

    def get_actors(self):
        ret_set = set()
        for call in self.callings:
            call_actors = call.getActors()
            ret_set.update(call_actors)
        return ret_set

    def get_topics(self):
        ret_set = set()
        for call in self.callings:
            ret_set.update(call.topics)
        return ret_set

    def copy_callings_actors(self, actor):
        new_calls: List[MsgData] = []
        for call in self.callings:
            if call.haveActor(actor):
                new_call = call.copy()
                new_calls.append(new_call)
        graph = SequenceGraph()
        graph.callings = new_calls
        return graph

    def copy_callings_topics(self, label):
        new_calls: List[MsgData] = []
        for call in self.callings:
            if call.haveLabel(label):
                new_call = call.copy()
                new_calls.append(new_call)
        graph = SequenceGraph()
        graph.callings = new_calls
        return graph

    def filter_messages(self, node_name):
        new_calls: List[MsgData] = []
        ## call: MsgData
        for call in self.callings:
            if node_name == call.pub:
                new_calls.append(call)
            elif node_name in call.subs:
                call.subs = set([node_name])
                new_calls.append(call)
        self.callings = new_calls


## ===================================================================


@dataclass
class NodeData:
    name: str = None
    suburl: str = None
    excluded: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {})

    def __getitem__(self, key):
        if key == 0:
            return self.name
        if key == 1:
            return self.suburl
        if key == 2:
            return self.excluded
        raise IndexError(f"invalid index: {key}")

    @staticmethod
    def sort_list(items_list: List["NodeData"]):
        items_list.sort(key=lambda x: x.name)


@dataclass
class TopicData:
    name: str = None
    pubs: List[str] = field(default_factory=lambda: [])
    subs: List[str] = field(default_factory=lambda: [])

    msgcount: int = 0
    excluded: bool = False
    suburl: str = None
    msgtype = None

    def __getitem__(self, key):
        if key == 0:
            return self.name
        if key == 1:
            return self.msgcount
        if key == 2:
            return self.excluded
        raise IndexError(f"invalid index: {key}")

    def is_connected_to_node(self, node_name):
        if node_name in self.pubs:
            return True
        if node_name in self.subs:
            return True
        return False

    @staticmethod
    def sort_list(items_list: List["TopicData"]):
        items_list.sort(key=lambda x: x.name)


@dataclass
class DiagramData:
    seq_diagram: SequenceGraph = None
    params: Dict[str, Any] = field(default_factory=lambda: {})
    nodes: List[NodeData] = field(default_factory=lambda: [])
    topics: List[TopicData] = field(default_factory=lambda: [])
    root_subdir = ""

    def get_node_by_name(self, name) -> NodeData:
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def get_topic_by_name(self, name) -> TopicData:
        for topic in self.topics:
            if topic.name == name:
                return topic
        return None

    def get_connected_topics(self, node_name) -> List[str]:
        ret_list = []
        ## topic: TopicData
        for topic in self.topics:
            if topic.is_connected_to_node(node_name):
                ret_list.append(topic.name)
        return ret_list

    def get_nodes_urls(self, node_names):
        labels_list = []
        for node_name in node_names:
            node_obj: NodeData = self.get_node_by_name(node_name)
            if node_obj:
                item_path = os.path.join(self.root_subdir, node_obj.suburl)
                labels_list.append((node_name, item_path))
            else:
                labels_list.append((node_name, None))
        return labels_list

    def get_topics_urls(self, topic_names):
        labels_list = []
        for topic_name in topic_names:
            topic_obj: TopicData = self.get_topic_by_name(topic_name)
            if topic_obj:
                item_path = os.path.join(self.root_subdir, topic_obj.suburl)
                labels_list.append((topic_name, item_path))
            else:
                labels_list.append((topic_name, None))
        return labels_list

    def filter_nodes(self, names):
        ret_list = []
        for node in self.nodes:
            if node.name in names:
                ret_list.append(node)
        return ret_list

    def filter_topics(self, names):
        ret_list = []
        for topic in self.topics:
            if topic.name in names:
                ret_list.append(topic)
        return ret_list

    def sort_nodes(self):
        self.nodes = sorted(self.nodes, key=lambda x: x.name)

    def sort_topics(self):
        self.topics = sorted(self.topics, key=lambda x: (-x.msgcount, x.name))


## =============================================================


def detect_sequence(data_list, item_hash_function):
    seq_detector = SequenceDetector(data_list, item_hash_function)
    return seq_detector.detect()


##
class SequenceDetector:

    def __init__(self, data_list, item_hash_function):
        self.hash_list = []
        for item in data_list:
            value = item_hash_function(item)
            self.hash_list.append(value)
        self.list_len = len(self.hash_list)

        self.best_seq = [0, 0, 0]
        self.best_gain = 0

    def detect(self):
        self.best_seq = [0, 0, 0]
        self.best_gain = 0
        max_seq_len = min(100, self.list_len)
        for seq_len in range(1, max_seq_len):
            seq = self.detect_seq(seq_len)
            seq_gain = calculate_seq_gain(seq)
            if seq_gain > self.best_gain:
                self.best_seq = seq
                self.best_gain = seq_gain
        return self.best_seq

    def detect_seq(self, seq_len):
        seq_max = self.list_len - seq_len + 1
        best_seq = [0, 0, 0]
        for start_index in range(0, self.list_len):
            pot_repeat = (self.list_len - start_index) / seq_len
            pot_gain = calculate_seq_gain([start_index, seq_len, pot_repeat])
            if pot_gain < self.best_gain:
                break
            seq_repeat = 1
            for next_index in range(start_index + seq_len, seq_max, seq_len):
                if self.compare_seq(start_index, next_index, seq_len) is False:
                    break
                seq_repeat += 1
            if seq_repeat > best_seq[2]:
                best_seq = (start_index, seq_len, seq_repeat)
        return best_seq

    def compare_seq(self, first_index, second_index, seq_len):
        for i in range(0, seq_len):
            if self.hash_list[first_index + i] != self.hash_list[second_index + i]:
                return False
        return True


def calculate_seq_gain(seq):
    seq_length = seq[1] * seq[2]
    return seq_length - seq[1]
