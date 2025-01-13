#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import Dict, List, Any, Tuple
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
        self._raw: List[Tuple[str, Any]] = []  # props list is needed in "constructor" entry type
        self._chains: Dict[str, List[Entry]] = {}
        self._chained = False  # is chain converted?
        super().__init__(props_dict)

    # prevents recursive error
    def __str__(self) -> str:
        obj_dict = dict(self)
        return obj_dict.__str__()

    # prevents recursive error
    def __repr__(self) -> str:
        return f"<Entry {self._id} {self._type}>"

    def get_id(self):
        return self._id

    def get_type(self):
        return self._type

    def get_chains(self):
        return self._chains

    def set_chained(self, value: bool):
        self._chained = value

    def get_list(self, prop):
        prop_item = self.get(prop)
        if prop_item is not None:
            return [prop_item]

        ret_list = []
        item_index = 0
        while True:
            index_str = f"{prop}_{item_index}"
            item_index += 1
            item_entry = self.get(index_str)
            if item_entry is None:
                break
            ret_list.append(item_entry)

        if not ret_list:
            entry_chains = self.get_chains()
            prop_items = entry_chains.get(prop, [])
            ret_list.extend(prop_items)

        return ret_list

    def get_ordered_tuples(self, props_list: List[str]) -> List[List[Any]]:
        if not self._raw:
            # empty or extra added entry (during graph conversion)
            ret_tuple = []
            for prop in props_list:
                prop_val = self.get(prop)
                ret_tuple.append(prop_val)
            return [ret_tuple]

        # regular entry
        ret_list = []
        tuple_size = len(props_list)
        ret_tuple = [None] * tuple_size
        found_list = [False] * tuple_size
        for prop_key, prop_val in self._raw:
            if prop_key not in props_list:
                continue
            prop_index = props_list.index(prop_key)
            last_index = get_last_index_of(found_list, True)
            if last_index >= prop_index:
                # if ret_tuple[0] is None:
                #     ret_tuple[0] = len(ret_list)
                ret_list.append(ret_tuple)
                ret_tuple = [None] * tuple_size
                found_list = [False] * tuple_size
            found_list[prop_index] = True
            ret_tuple[prop_index] = prop_val
        if True in found_list:
            # if ret_tuple[0] is None:
            #     ret_tuple[0] = len(ret_list)
            ret_list.append(ret_tuple)
        return ret_list

    def get_sub_entries(self, prop=None) -> List[Tuple[str, "Entry"]]:
        ret_list = []
        if prop is not None:
            entry_chains = self.get_chains()
            prop_items = entry_chains.get(prop, [])
            for chain_item in prop_items:
                ret_list.append((prop, chain_item))
            self_item = self.get(prop)
            if self_item is not None:
                data = (prop, self_item)
                if data not in ret_list:
                    ret_list.append(data)
        else:
            entry_chains = self.get_chains()
            chain_props = set()
            for chain_prop, chain_list in entry_chains.items():
                chain_props.add(chain_prop)
                for chain_item in chain_list:
                    ret_list.append((chain_prop, chain_item))
            for subprop, subentry in self.items():
                if is_entry_prop_internal(subprop):
                    continue
                if self._chained and subprop == "chain":
                    continue
                if subprop in chain_props:
                    ## already added
                    continue
                ret_list.append((subprop, subentry))
        return sorted(ret_list, key=lambda container: container[0])

    def replace_data(self, prop, old_value, new_value):
        self[prop] = new_value
        for raw_index, raw_data in enumerate(self._raw.copy()):
            if raw_data[0] != prop:
                continue
            if raw_data[1] != old_value:
                continue
            self._raw[raw_index] = (raw_data[0], new_value)


def get_last_index_of(container, value):
    if value not in container:
        return -1
    index_of = container[::-1].index(value)
    return len(container) - 1 - index_of


class LangContent:

    def __init__(self, content_dict):
        # id: ( id, type, list of (prop, val) )
        self.content_lines: Dict[str, Tuple[str, str, List[Tuple[str, str]]]] = content_dict  # raw text lines

        self._entry_id_counter = None

        # dict with found types and it's properties
        self.types_fields = None

        # Entries tree
        # dict keys are entry ids (e.g. @123) values are 'Entry' objects
        self.content_objs: Dict[str, Entry] = self._objectify()

        self.parents_dict: Dict[str, List[Tuple[Entry, str]]] = None
        self.ancestors_dict: Dict[str, List[List[Tuple[Entry, str]]]] = None

    def _objectify(self):
        ret_objs_dict = {}
        for key, entry in self.content_lines.items():
            entry_type = entry[1]
            props_list = entry[2]
            props_dict = props_list_to_dict(props_list)
            obj_dict = {"_id": key, "_type": entry_type, "_raw": props_list.copy()}
            obj_dict.update(props_dict)
            obj_dict = dict(sorted(obj_dict.items()))  # sort by keys
            ret_objs_dict[key] = Entry(obj_dict)

        ## convert entry ids to references
        for _key, object_item in ret_objs_dict.items():
            for field, value in object_item.items():
                if field == "_raw":
                    for prop_index, prop_data in enumerate(value):
                        prop_val = prop_data[1]
                        if prop_val.startswith("@"):
                            prop_key = prop_data[0]
                            prop_entry = ret_objs_dict[prop_val]
                            value[prop_index] = (prop_key, prop_entry)
                    continue

                if is_entry_prop_internal(field):
                    continue
                if value.startswith("@"):
                    object_item[field] = ret_objs_dict[value]

        return ret_objs_dict

    def _get_next_entry_id(self):
        if self._entry_id_counter is None:
            self._entry_id_counter = 0
            for entry in self.content_objs.values():
                entry_id = entry.get_id()[1:]
                entry_id = int(entry_id)
                if entry_id > self._entry_id_counter:
                    self._entry_id_counter = entry_id

        self._entry_id_counter += 1
        return f"@{self._entry_id_counter}"

    def _add_entry(self, entry: Entry):
        entry_id = entry.get_id()
        self.content_objs[entry_id] = entry

    def get_types_fields(self):
        if self.types_fields is not None:
            return self.types_fields

        ret_types_dict: Dict[str, Dict[str, Any]] = {}
        for _key, entry in self.content_lines.items():
            entry_type = entry[1]
            entry_list = entry[2]
            entry_data = props_list_to_dict(entry_list)

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

        self.types_fields = ret_types_dict
        return self.types_fields

    def size(self):
        return len(self.content_objs)

    def get_root_entry(self):
        return list(self.content_objs.values())[0]

    # entry_id with "@" in front
    def get_entry_by_id(self, entry_id):
        return self.content_objs.get(entry_id)

    def get_entries(self, entry_property) -> List[Entry]:
        ret_list = []
        # entry: Entry
        for entry in self.content_objs.values():
            sub_entries = entry.get_sub_entries(entry_property)
            for item in sub_entries:
                ret_list.append(item[1])
        return ret_list

    # returns dict: {entry_id: [(parent_entry, prop_in_parent)]}
    def get_parents_dict(self) -> Dict[str, List[Tuple[Entry, str]]]:
        if self.parents_dict is not None:
            return self.parents_dict

        self.parents_dict = {}
        # entry: Entry
        for entry in self.content_objs.values():
            for entry_prop, entry_val in entry.get_sub_entries():
                if is_entry_prop_internal(entry_prop):
                    continue
                if not isinstance(entry_val, Entry):
                    continue
                dep_id = entry_val.get_id()
                dep_list: List[Tuple[Entry, str]] = self.parents_dict.get(dep_id, [])
                dep_list.append((entry, entry_prop))
                self.parents_dict[dep_id] = dep_list

        return self.parents_dict

    def get_ancestors_dict(self):
        if self.ancestors_dict is not None:
            return self.ancestors_dict

        def visitor(ancestors_list, ret_dict):
            curr_data = ancestors_list[-1]
            entry = curr_data[1]
            if not isinstance(entry, Entry):
                return False
            entry_id = entry.get_id()

            entry_ancestors = ret_dict.get(entry_id)
            if entry_ancestors is None:
                entry_ancestors = []
                ret_dict[entry_id] = entry_ancestors

            # parent_ancestors_lists = ancestors_list[:-1]
            entry_ancestors.append(ancestors_list.copy())

            # # curr_ancestors = ret_dict.get(entry_id)
            # # if curr_ancestors is None:
            # #     curr_ancestors = []
            # # ret_dict[entry_id] = curr_ancestors
            #
            # # if curr_ancestors:
            # #     # already found - skip
            # #     return False
            # if len(ancestors_list) < 2:
            #     return True
            #
            # parent_data = ancestors_list[-2]
            # parent_entry = parent_data[1]
            # parent_prop = curr_data[0]
            # parent_id = parent_entry.get_id()
            # parent_ancestors_lists = ret_dict.get(parent_id, [])
            # if not parent_ancestors_lists:
            #     # empty list - add first item
            #     new_list = []
            #     curr_ancestors = [(parent_entry, parent_prop)]
            #     new_list.append(curr_ancestors)
            #     ret_dict[entry_id] = new_list
            # else:
            #     new_list = []
            #     for parent_ancestors in parent_ancestors_lists:
            #         curr_ancestors = parent_ancestors.copy()
            #         curr_ancestors.append((parent_entry, parent_prop))
            #         new_list.append(curr_ancestors)
            #     ret_dict[entry_id] = new_list

            return True

        traversal = EntryGraphBreadthFirstTraversal()
        root_entry = self.get_root_entry()
        self.ancestors_dict = {}
        traversal.visit_graph(root_entry, visitor, self.ancestors_dict)

        return self.ancestors_dict

    def convert_entries(self):
        self.convert_chain()
        self.convert_chan()

    def convert_chain(self):
        self.parents_dict = None
        self.ancestors_dict = None

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

    def convert_chan(self):
        self.parents_dict = None
        self.ancestors_dict = None

        # entry: Entry
        for entry in list(self.content_objs.values()):
            if entry.get_type() == "tree_vec":
                continue
            for prop, value in list(entry.items()):
                # if prop != "chan":
                #     continue
                if not isinstance(value, Entry):
                    continue
                if value.get_type() != "tree_list":
                    continue

                chan_list = self._get_tree_list_entries(value)
                if not chan_list:
                    continue
                next_id = self._get_next_entry_id()
                len_str = str(len(chan_list))
                entry_data = {"_id": next_id, "_type": "tree_vec", "lngt": len_str}
                for index, item in enumerate(chan_list):
                    index_str = str(index)
                    entry_data[index_str] = item
                tree_vec_entry = Entry(entry_data)
                self._add_entry(tree_vec_entry)
                entry.replace_data(prop, value, tree_vec_entry)

    def _get_chain_entries(self, chain_start: Entry):
        ret_list = []
        chain_item = chain_start
        while chain_item:
            ret_list.append(chain_item)
            chain_item = chain_item.get("chain")
        return ret_list

    def _get_tree_list_entries(self, tree_list_start: Entry):
        ret_list = []
        tree_list_item = tree_list_start
        while tree_list_item:
            ret_list.append(tree_list_item)
            next_item = tree_list_item.get("chan")
            if next_item:
                del tree_list_item["chan"]
            tree_list_item = next_item
        return ret_list

    def print_types_fields(self):
        pprint.pprint(self.types_fields, indent=4)

    def print_lines(self):
        for entry in self.content_lines.values():
            print(entry)


def props_list_to_dict(props_list: List[Tuple[str, str]]) -> Dict[str, Any]:
    ret_dict: Dict[str, Any] = {}
    for next_key, next_val in props_list:
        sublist = ret_dict.get(next_key)
        if sublist is None:
            sublist = []
            ret_dict[next_key] = sublist
        sublist.append(next_val)

    ## convert lists
    for key, val_list in list(ret_dict.items()):
        if len(val_list) < 2:
            ## reduce list
            val = val_list[0]
            ret_dict[key] = val
            continue
        # for backward compatibility convert list to list of keys with index like "{prop}_0" etc
        del ret_dict[key]
        for index, item in enumerate(val_list):
            new_key = f"{key}_{index}"
            ret_dict[new_key] = item

    return ret_dict


def is_entry_prop_chain(prop: str):
    return prop in ("args", "dcls", "flds", "vars")


def is_entry_prop_internal(prop: str):
    return prop.startswith("_")


def is_entry_language_internal(entry: Entry):
    if not isinstance(entry, Entry):
        return False
    entry_name = get_entry_name(entry)
    if entry_name and entry_name.startswith("._anon_"):
        # internal - do not go deeper
        return True
    if entry.get_type() == "field_decl":
        if not entry_name:
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "function_decl":
        entry_body_list = entry.get_list("body")
        if entry_body_list is None:
            # no body - internal function
            return True
        if "undefined" in entry_body_list and len(entry_body_list) == 1:
            # no body - internal function
            return True
        return False
    if entry.get_type() == "namespace_decl":
        if entry_name == "std" or entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "type_decl":
        if entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "record_type":
        if entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        if entry_name.startswith("._anon_"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "function_decl":
        if entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "identifier_node":
        if entry_name.startswith("__"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "var_decl":
        if entry_name.startswith("_ZT"):
            # internal - do not go deeper
            return True
        return False
    if entry.get_type() == "const_decl":
        if entry_name.startswith("__IS"):
            # internal - do not go deeper
            return True
        return False
    return False


def is_namespace_internal(namepace_list):
    copied_list = namepace_list.copy()
    copied_list = [value for value in copied_list if value != ""]  # remove empty elements
    if not copied_list:
        # empty list
        return False
    if copied_list[0] == "std":
        return True
    for name in namepace_list:
        if name.startswith("__"):
            return True
    return False


def print_entry_graph(entry: Entry):
    nodes_list = EntryGraphDepthFirstTraversal.to_list(entry)
    for curr_item, level, node_data in nodes_list:
        indent = " " * level
        if isinstance(curr_item, Entry):
            print(f"{indent}{node_data}: {curr_item.get_id()} {curr_item.get_type()}")
        else:
            print(f"{indent}{node_data}: {curr_item}")


## ======================================================================


def get_entry_repr(entry: Entry) -> str:
    if not isinstance(entry, Entry):
        return entry

    type_name = get_type_entry_name(entry)
    if type_name is not None:
        return type_name

    num_value = get_number_entry_value(entry, fail_exception=False)
    if num_value is not None:
        return num_value

    if entry.get_type() == "field_decl":
        ## in case of base classes field_decls does not have any name
        field_name = get_entry_name(entry, None)
        if field_name:
            return field_name
        field_type = entry.get("type")
        return get_entry_repr(field_type)

    return get_entry_name(entry)


def get_type_entry_name(type_entry: Entry):
    name, mod = get_type_name_mod(type_entry)
    if name is None:
        return None
    if mod is None:
        return name
    return f"{mod} {name}"


def get_type_name_mod(type_entry: Entry):
    parm_mod = None
    arg_qual = type_entry.get("qual")
    if arg_qual == "c":
        parm_mod = "const"

    entry_type = type_entry.get_type()

    if entry_type == "pointer_type":
        ptd = type_entry.get("ptd")
        ptd_name = get_full_name(ptd)
        ptd_qual = ptd.get("qual")
        if ptd_qual == "c":
            ptd_name += " const"
        ptd_name += " *"
        return (ptd_name, parm_mod)

    if entry_type == "reference_type":
        refd = type_entry.get("refd")
        refd_name = get_full_name(refd)
        refd_qual = refd.get("qual")
        if refd_qual == "c":
            refd_name += " const"
        refd_name += " &"
        return (refd_name, parm_mod)

    if entry_type == "array_type":
        elms = type_entry.get("elts")
        elms_name = get_full_name(elms)
        return (f"{elms_name}[]", parm_mod)

    name_list = get_decl_namespace_list(type_entry)
    if name_list:
        param_name = "::".join(name_list)
        return (param_name, parm_mod)

    param_name = get_entry_name(type_entry, default_ret=None)
    return (param_name, parm_mod)


def get_full_name(entry: Entry) -> str:
    if entry.get_type() == "record_type":
        ns_list = get_record_namespace_list(entry)
        return "::".join(ns_list)
    return get_entry_name(entry)


def get_record_namespace_list(record_type: Entry) -> List[str]:
    if record_type is None:
        return []
    field_type = record_type.get("name")
    ret_list = get_decl_namespace_list(field_type)
    return ret_list


# decl_entry: type_decl, record_decl, function_decl etc.
def get_decl_namespace_list(decl_entry: Entry) -> List[str]:
    if decl_entry is None:
        return []

    ret_list: List[str] = []
    item = decl_entry
    while item:
        item_type = item.get_type()
        if item_type == "translation_unit_decl":
            if not ret_list:
                break
            if ret_list[-1] == "::":
                # top namespace found
                break
            ret_list.append("")  # required to append "::" at top level
            break
        if item_type == "record_type":
            # happens in case of method declaration
            record_list = get_record_namespace_list(item)
            record_list.reverse()
            ret_list.extend(record_list)
            break

        item_name_entry = item.get("name")
        item_name = get_entry_name(item_name_entry)
        if item_name is None:
            # not a type?
            return None
        ret_list.append(item_name)
        item = item.get("scpe")

    ret_list.reverse()
    return ret_list


def get_entry_name(entry: Entry, default_ret="[--unknown--]") -> str:
    if not isinstance(entry, Entry):
        return entry

    entry_value = entry.get("name")
    if entry_value is not None:
        return get_entry_name(entry_value)

    entry_type = entry.get_type()
    if entry_type == "identifier_node":
        entry_value = entry.get("strg", "[--no entry--]")
        return get_entry_name(entry_value)

    return default_ret


def get_number_entry_value(value: Entry, fail_exception=True):
    if value is None:
        raise RuntimeError("None not supported")

    value_type = value.get_type()

    if value_type == "integer_cst":
        return value.get("int")

    if value_type == "real_cst":
        return value.get("valu")

    if value_type == "string_cst":
        return value.get("strg")

    if fail_exception:
        raise RuntimeError("unhandled number entry: {value_type}, {value.get_id()}")
    return None


# ============================================


class EntryGraphAbstractTraversal(GraphAbstractTraversal):
    def visit_graph(self, node, visitor, visitor_context=None):
        return self._visit_graph([(None, node)], visitor, visitor_context)

    def _get_node_id(self, item_data) -> Any:
        curr_data = item_data[-1]
        item = curr_data[1]
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
        subentries = get_sub_entries(item_data)
        rev_list = reversed(subentries)
        self.visit_list.extendleft(rev_list)


class EntryGraphBreadthFirstTraversal(EntryGraphAbstractTraversal):
    def _add_subnodes(self, item_data):
        subentries = get_sub_entries(item_data)
        self.visit_list.extend(subentries)


def get_sub_entries(ancestors_list: List[Tuple[str, Entry]]) -> List[List[Tuple[str, Entry]]]:
    entry_data = ancestors_list[-1]
    entry: Entry = entry_data[1]
    sub_entries = entry.get_sub_entries()
    ret_list = []
    for prop, subentry in sub_entries:
        ret_list.append(ancestors_list + [(prop, subentry)])
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
        self.include_internals = include_internals
        self.depth_first = depth_first
        self.root = get_entry_tree(self.content, include_internals, depth_first)
        return self.root

    def get_filtered_nodes(self):
        return filter_repeated_entries(self.root, self.depth_first)


def get_entry_tree(content: LangContent, include_internals=False, depth_first=False) -> EntryTreeNode:
    content.convert_entries()
    first_entry = content.get_root_entry()

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
        return get_entry_tree_subnodes(ancestors_list)

    def _get_current_item(self, ancestors_list):
        return ancestors_list[-1]

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
        return get_entry_tree_subnodes(ancestors_list)

    def _get_current_item(self, ancestors_list):
        return ancestors_list[-1]

    @classmethod
    def traverse(cls, node: EntryTreeNode, visitor, visitor_context=None):
        traversal = cls()
        traversal.visit_tree(node, visitor, visitor_context)

    @classmethod
    def to_list(cls, node: EntryTreeNode):
        traversal = cls()
        return get_nodes_from_tree(node, traversal)


def get_entry_tree_subnodes(ancestors_list):
    curr_node: EntryTreeNode = ancestors_list[-1]
    ret_list = []
    for subnode in curr_node.items:
        ret_list.append(ancestors_list + [subnode])
    return ret_list


def print_entry_tree(entry_tree: EntryTreeNode, indent=2) -> str:
    ret_content = []
    nodes_list = EntryTreeDepthFirstTraversal.to_list(entry_tree)
    for curr_item, level in nodes_list:
        spaces = " " * level * indent
        prop = ""
        if curr_item.property is not None:
            prop = f"{curr_item.property}: "
        ret_content.append(f"{spaces}{prop}entry: {curr_item.entry} items num: {len(curr_item.items)}\n")
    return "".join(ret_content)


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

    def convert_item(self, ancestors_list, _context=None):
        curr_data = ancestors_list[-1]
        entry = curr_data[1]
        if isinstance(entry, Entry):
            if not self.include_internals:
                if is_entry_language_internal(entry):
                    return False

        prop = curr_data[0]
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
        return "".join([entry_data[1].get_id() for entry_data in entries_list])


def create_entry_tree_depth_first(entry: Entry, include_internals=False) -> EntryTreeNode:
    traversal = EntryGraphDepthFirstTraversal()
    converter = EntryTreeConverter(include_internals=include_internals)
    return converter.convert(entry, traversal)
