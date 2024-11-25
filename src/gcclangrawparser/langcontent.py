#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import Dict, List, Any
from collections import namedtuple
import pprint

from munch import Munch

from gcclangrawparser.abstracttraversal import (
    GraphAbstractTraversal,
    get_nodes_from_tree,
    get_nodes_from_graph,
    DepthFirstTreeTraversal,
    BreadthFirstTreeTraversal,
    get_nodes_from_tree_ancestors,
    TreeAbstractTraversal,
)


# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


class Entry(Munch):
    """Base project representing entry in lang raw file.

    Access to object data is possible through dict interface (array operator) or by dot operator.
    """

    def __init__(self, props_dict):
        self._id = None
        self._type = None
        self._chains = {}
        self._chained = False  # is chain converted?
        super().__init__(props_dict)

    # prevents recursive error
    def __str__(self) -> str:
        obj_dict = dict(self)
        return obj_dict.__str__()

    # prevents recursive error
    def __repr__(self) -> str:
        return f"<Entry {self._id}>"

    def get_id(self):
        return self._id

    def get_type(self):
        return self._type

    def get_chains(self):
        return self._chains

    def set_chained(self, value: bool):
        self._chained = value

    def get_sub_entries(self):
        ret_list = []
        entry_chains = self.get_chains()
        chain_props = set()
        for chain_prop, chain_list in entry_chains.items():
            chain_props.add(chain_prop)
            for chain_item in chain_list:
                ret_list.append((chain_prop, chain_item))
        for prop, subentry in self.items():
            if is_entry_prop_internal(prop):
                continue
            if self._chained and prop == "chain":
                continue
            if prop in chain_props:
                ## already added
                continue
            ret_list.append((prop, subentry))
        return sorted(ret_list, key=lambda container: container[0])


class LangContent:

    def __init__(self, content_dict):
        self.content_lines = content_dict  # raw text lines

        # dict with found types and it's properties
        self.types_fields = self._prepare_types_fields()

        # Entries tree
        # dict keys are entry ids (e.g. @123) values are 'Entry' objects
        self.content_objs: Dict[str, Entry] = self._objectify()

    def _prepare_types_fields(self):
        ret_types_dict = {}
        for _key, entry in self.content_lines.items():
            entry_type = entry[1]
            entry_data = entry[2]

            type_props = ret_types_dict.get(entry_type, {})

            optional_props = set()
            curr_props = set(type_props.keys())
            if curr_props:
                new_props = set(entry_data.keys())
                optional_props.update(curr_props.difference(new_props))
                optional_props.update(new_props.difference(curr_props))

            for prop_key, prop_val in entry_data.items():
                if entry_type == "identifier_node":
                    if prop_key == "strg":
                        type_props[prop_key] = {"mandatory": True, "values": ["<string>"]}
                        continue
                    if prop_key == "lngt":
                        type_props[prop_key] = {"mandatory": True, "values": ["<unsigned number>"]}
                        continue
                if entry_type == "integer_cst":
                    if prop_key == "int":
                        type_props[prop_key] = {"mandatory": True, "values": ["<number>"]}
                        continue

                props_data = type_props.get(prop_key, {"mandatory": True, "values": []})
                prop_values = props_data["values"]
                prop_values = set(prop_values)
                if prop_val.startswith("@"):
                    # identifier
                    prop_values.add("<entry-id>")
                    prop_value_types = props_data.get("allowedtypes", [])
                    prop_value_types = set(prop_value_types)
                    linked_element = self.content_lines[prop_val]
                    linked_type = linked_element[1]
                    prop_value_types.update([linked_type])
                    props_data["allowedtypes"] = sorted(prop_value_types)
                else:
                    prop_values.add(prop_val)
                props_data["values"] = sorted(prop_values)
                type_props[prop_key] = props_data

            if curr_props:
                for op_key in optional_props:
                    props_data = type_props[op_key]
                    props_data["mandatory"] = False

            type_props = dict(sorted(type_props.items()))
            ret_types_dict[entry_type] = type_props
        ret_types_dict = dict(sorted(ret_types_dict.items()))

        return ret_types_dict

    def _objectify(self):
        ret_objs_dict = {}
        for key, entry in self.content_lines.items():
            entry_type = entry[1]
            entry_data = entry[2]
            obj_dict = {"_id": key, "_type": entry_type}
            obj_dict.update(entry_data)
            obj_dict = dict(sorted(obj_dict.items()))  # sort by keys
            ret_objs_dict[key] = Entry(obj_dict)
        for _key, object_item in ret_objs_dict.items():
            for field, value in object_item.items():
                if is_entry_prop_internal(field):
                    continue
                if value.startswith("@"):
                    object_item[field] = ret_objs_dict[value]
        return ret_objs_dict

    def size(self):
        return len(self.content_objs)

    def convert_chains(self):
        for entry in self.content_objs.values():
            for prop, value in list(entry.items()):
                if not is_entry_prop_chain(prop):
                    continue
                if not isinstance(value, Entry):
                    continue
                # chain first item found
                chain_list = self._get_chain_entries(value)
                entry_chains = entry.get_chains()
                entry_chains[prop] = chain_list
                for chain_item in chain_list:
                    chain_item.set_chained(True)

                # del entry[prop]
                # for index, chain_entry in enumerate(chain_list):
                #     prop_key = f"{prop}_{index:0>5}"
                #     entry[prop_key] = chain_entry
                #     if "chain" in chain_entry:
                #         del chain_entry["chain"]

    def _get_chain_entries(self, chain_start: Entry):
        ret_list = []
        chain_item = chain_start
        while chain_item:
            ret_list.append(chain_item)
            chain_item = chain_item.get("chain")
        return ret_list

    def print_types_fields(self):
        pprint.pprint(self.types_fields, indent=4)

    def print_entries(self):
        for entry in self.content_lines.values():
            print(entry)

    def print_namespaces(self):
        find_type = "namespace_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                scope_obj = entry["scpe"]
                scope_name = get_entry_name(scope_obj)
                source_point = entry["srcp"]
                lang = entry.get("lang", "<--no entry-->")
                type_name = entry.get("type", "<--no entry-->")
                type_name = get_entry_name(type_name)
                print(f"{entry.get_id()}: {entry.get_type()}")
                print(f"    name: {entry_name}")
                print(f"    scpe: {scope_name}")
                print(f"    lang: {lang}")
                print(f"    srcp: {source_point}")
                print(f"    type: {type_name}")
                ## chain - not important?
                ## dcls - not important? can be assumed from 'scpe' of other entries pointing to the namespace

    def print_translation_units(self):
        find_type = "translation_unit_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                print(f"{entry.get_id()}: {entry_name}")

    def print_functions(self):
        find_type = "function_decl"
        print(f"{find_type}:")
        print(f"    allowed props: {self.types_fields[find_type]}")
        for entry in self.content_objs.values():
            if entry.get_type() == find_type:
                entry_name = get_entry_name(entry)
                mngl_name = entry.get("mngl", "<--no entry-->")
                mngl_name = get_entry_name(mngl_name)
                # type_name = entry.get("type", "<--no entry-->")
                # type_name = get_entry_name(type_name)
                print(f"{entry.get_id()} -> {entry.get_type()}")
                print(f"    name: {entry_name}")
                print(f"    mngl: {mngl_name}")
                # print(f"    type: {type_name}")

    # def get_name(self, entry_id, optional=False, default=None):
    #     identifier_entry = self.content_lines[entry_id]
    #     identifier_props = identifier_entry[2]
    #     try:
    #         if optional:
    #             return identifier_props.get("strg", default)
    #         return identifier_props["strg"]
    #     except KeyError:
    #         print(f"invalid props - key: {entry_id} props: {identifier_props}")
    #         raise
    #
    # def get_scope_name(self, entry_id, optional=False, default=None):
    #     identifier_entry = self.content_lines[entry_id]
    #     identifier_props = identifier_entry[2]
    #     try:
    #         if optional:
    #             return identifier_props.get("name", default)
    #         return identifier_props["name"]
    #     except KeyError:
    #         print(f"invalid props - key: {entry_id} props: {identifier_props}")
    #         raise


def is_entry_prop_chain(prop: str):
    return prop in ("args", "dcls", "flds")


def is_entry_prop_internal(prop: str):
    return prop.startswith("_")


def is_entry_language_internal(entry: Entry):
    if not isinstance(entry, Entry):
        return False
    if entry.get_type() == "field_decl":
        entry_name = get_entry_name(entry)
        if not entry_name:
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "function_decl":
        entry_body = entry.get("body")
        if entry_body is None:
            # no body - internal function
            return True
        if entry_body == "undefined":
            # no body - internal function
            return True
        return False
    if entry.get_type() == "namespace_decl":
        entry_name = get_entry_name(entry)
        if entry_name == "std" or entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "type_decl":
        entry_name = get_entry_name(entry)
        if entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    return False


def print_entry_graph(entry: Entry):
    nodes_list = EntryGraphDepthFirstTraversal.to_list(entry)
    for curr_item, level, node_data in nodes_list:
        indent = " " * level
        if isinstance(curr_item, Entry):
            print(f"{indent}{node_data}: {curr_item.get_id()} {curr_item.get_type()}")
        else:
            print(f"{indent}{node_data}: {curr_item}")


def get_entry_name(entry: Entry):
    if not isinstance(entry, Entry):
        return entry

    entry_type = entry.get_type()

    if entry_type == "integer_type":
        label = ""
        entry_value = entry.get("name")
        if entry_value is not None:
            label = get_entry_name(entry_value)

        entry_qual = entry.get("qual")
        qual_label = get_entry_name(entry_qual)
        if qual_label is not None:
            if qual_label == "c":
                label = "const " + label
            else:
                raise RuntimeError(f"unhandled case for {entry.get_id()}")
        return label

    entry_value = entry.get("name")
    if entry_value is not None:
        return get_entry_name(entry_value)

    if entry_type == "type_decl":
        entry_value = entry["type"]
        return get_entry_name(entry_value)

    if entry_type == "identifier_node":
        try:
            entry_value = entry.get("strg", "[--no entry--]")
            return get_entry_name(entry_value)
        except KeyError:
            print(f"invalid props - {entry}")
            raise

    if entry_type == "pointer_type":
        entry_value = entry["ptd"]
        return get_entry_name(entry_value)

    if entry_type == "function_type":
        entry_value = entry["retn"]
        return get_entry_name(entry_value)

    if entry_type == "integer_cst":
        entry_value = entry["int"]
        return get_entry_name(entry_value)

    if entry_type == "complex_type":
        return "[unknown]"

    return f"[unhandled entry type: {entry.get_id()} {entry_type}]"


# ============================================


class EntryGraphAbstractTraversal(GraphAbstractTraversal):
    def visit_graph(self, node, visitor, visitor_context=None):
        return self._visit_graph(([node], None), visitor, visitor_context)

    def _get_node_id(self, item_data) -> Any:
        ancestors_list = item_data[0]
        item = ancestors_list[-1]
        if not isinstance(item, Entry):
            return None
        return item.get_id()
        ### why tuple as id?
        ### it causes branches to be repeated/expanded
        # prop = item_data[1]
        # return (item.get_id(), prop)

    @classmethod
    def traverse(cls, entry: Entry, visitor):
        traversal = cls()
        traversal.visit_graph(entry, visitor)

    @classmethod
    def to_list(cls, entry: Entry):
        traversal = cls()
        return get_nodes_from_graph(entry, traversal)


class EntryGraphDepthFirstTraversal(EntryGraphAbstractTraversal):
    def _add_subnodes(self, item_data):
        ancestors_list = item_data[0]
        subentries = get_sub_entries(ancestors_list)
        rev_list = reversed(subentries)
        self.visit_list.extendleft(rev_list)


class EntryGraphBreadthFirstTraversal(EntryGraphAbstractTraversal):
    def _add_subnodes(self, item_data):
        ancestors_list = item_data[0]
        subentries = get_sub_entries(ancestors_list)
        self.visit_list.extend(subentries)


def get_sub_entries(ancestors_list: List[Entry]):
    ret_list = []
    entry: Entry = ancestors_list[-1]
    sub_entries = entry.get_sub_entries()
    for prop, subentry in sub_entries:
        ret_list.append((ancestors_list + [subentry], prop))
    return ret_list


# =========================================


EntryTreeNode = namedtuple("EntryTreeNode", ["entry", "property", "items"])


class EntryTree:

    def __init__(self, content: LangContent):
        self.content: LangContent = content
        self.root: EntryTreeNode = None
        self.include_internals: bool = False
        self.depth_first: bool = False

    def get_tree_root(self) -> EntryTreeNode:
        return self.root

    def generate_tree(self, include_internals=False, depth_first=False):
        self.include_internals: bool = include_internals
        self.depth_first = depth_first
        self.root = get_entry_tree(self.content, include_internals, depth_first)
        return self.root

    def get_filtered_nodes(self):
        return filter_repeated_entries(self.root, self.depth_first)


def get_entry_tree(content: LangContent, include_internals=False, depth_first=False) -> EntryTreeNode:
    content.convert_chains()
    first_entry = content.content_objs["@1"]

    traversal: EntryGraphAbstractTraversal = None
    if depth_first:
        traversal = EntryGraphDepthFirstTraversal()
    else:
        traversal = EntryGraphBreadthFirstTraversal()

    converter = EntryTreeConverter(include_internals=include_internals)
    return converter.convert(first_entry, traversal)


def filter_repeated_entries(entry_tree: EntryTreeNode, depth_first=False) -> List[List[EntryTreeNode]]:
    ## to properly work, the traversal have to be the same as traversal
    ## for creating the entry_tree

    traversal: TreeAbstractTraversal = None
    if depth_first:
        traversal = EntryTreeDepthFirstTraversal()
    else:
        traversal = EntryTreeBreadthFirstTraversal()

    node_list: List[List[EntryTreeNode]] = get_nodes_from_tree_ancestors(entry_tree, traversal)

    # nodes_dict = {}
    ret_list = []
    visited = set()
    for ancestors_list in node_list:
        node = ancestors_list[-1]
        entry = node.entry
        if not isinstance(entry, Entry):
            continue
        entry_id = entry.get_id()
        if entry_id in visited:
            continue
        visited.add(entry_id)
        ret_list.append(ancestors_list)

    return ret_list


def get_node_entry_id(node: EntryTreeNode):
    entry = node.entry
    if entry is None:
        return None
    if not isinstance(entry, Entry):
        return None
    return entry.get_id()


class EntryTreeDepthFirstTraversal(DepthFirstTreeTraversal):
    def _get_subnodes(self, ancestors_list):
        curr_node = ancestors_list[-1]
        ret_list = []
        for subnode in curr_node.items:
            ret_list.append((ancestors_list + [subnode], None))
        return ret_list

    @classmethod
    def traverse(cls, node: EntryTreeNode, visitor, visitor_context=None):
        traversal = cls()
        traversal.visit_tree(node, visitor, visitor_context)

    @classmethod
    def to_list(cls, node: EntryTreeNode):
        traversal = cls()
        return get_nodes_from_tree(node, traversal)


class EntryTreeBreadthFirstTraversal(BreadthFirstTreeTraversal):
    def _get_subnodes(self, ancestors_list):
        curr_node = ancestors_list[-1]
        ret_list = []
        for subnode in curr_node.items:
            ret_list.append((ancestors_list + [subnode], None))
        return ret_list

    @classmethod
    def traverse(cls, node: EntryTreeNode, visitor, visitor_context=None):
        traversal = cls()
        traversal.visit_tree(node, visitor, visitor_context)

    @classmethod
    def to_list(cls, node: EntryTreeNode):
        traversal = cls()
        return get_nodes_from_tree(node, traversal)


def print_entry_tree(entry_tree: EntryTreeNode, indent=2) -> str:
    ret_content = ""
    nodes_list = EntryTreeDepthFirstTraversal.to_list(entry_tree)
    for curr_item, level in nodes_list:
        spaces = " " * level * indent
        prop = ""
        if curr_item.property is not None:
            prop = f"{curr_item.property}: "
        ret_content += f"{spaces}{prop}entry: {curr_item.entry} items num: {len(curr_item.items)}\n"
    return ret_content


## ==================================================


# convert Entries graph to Entry tree
class EntryTreeConverter:

    def __init__(self, include_internals=False):
        self.include_internals = include_internals
        self.entry_node_dict = {}

    def convert(self, entry: Entry, traversal: GraphAbstractTraversal) -> EntryTreeNode:
        container_node = EntryTreeNode(None, None, [])
        self.entry_node_dict[""] = container_node
        traversal.visit_graph(entry, self.convert_item)

        root_list = container_node.items
        if len(root_list) != 1:
            raise RuntimeError("error while converting entry graph")

        root_node: EntryTreeNode = root_list[0]
        return root_node

    def convert_item(self, item_data, _context=None):
        ancestors_list: List[Entry] = item_data[0]
        entry = ancestors_list[-1]
        if isinstance(entry, Entry):
            if not self.include_internals:
                if is_entry_language_internal(entry):
                    return False

        prop = item_data[1]
        parents_list = ancestors_list[:-1]
        parent_node_id = self._get_entries_path(parents_list)
        parent_node = self.entry_node_dict[parent_node_id]

        new_node = EntryTreeNode(entry, prop, [])
        parent_node.items.append(new_node)
        parent_node.items.sort(key=lambda container: container[1])

        if isinstance(entry, Entry):
            entry_node_id = self._get_entries_path(ancestors_list)
            if entry_node_id not in self.entry_node_dict:
                ## sometimes one entry has two children with the same ID but different prop value
                ## we prefer first one to honor order of 'breadth first' and 'depth first' traversal
                self.entry_node_dict[entry_node_id] = new_node
            # if not self.include_internals:
            #     if is_entry_language_internal(entry):
            #         return False
        return True

    def _get_entries_path(self, entries_list):
        return "".join([entry.get_id() for entry in entries_list])


def create_entry_tree_depth_first(entry: Entry, include_internals=False) -> EntryTreeNode:
    traversal = EntryGraphDepthFirstTraversal()
    converter = EntryTreeConverter(include_internals=include_internals)
    return converter.convert(entry, traversal)
