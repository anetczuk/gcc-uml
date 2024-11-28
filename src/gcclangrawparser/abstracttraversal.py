#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
from collections import deque, namedtuple
from typing import List, Tuple, Any, Set


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# traverse graph
class GraphAbstractTraversal:
    def __init__(self):
        self.visit_list = None  # used in subclasses

    def visit_graph(self, node, visitor, visitor_context=None):
        # return self._visit_graph(node, visitor, visitor_context)
        raise NotImplementedError("not implemented")

    def _visit_graph(self, item_data, visitor, visitor_context=None):
        self.visit_list = deque([item_data])
        visited = set()
        while self.visit_list:
            item_data = self.visit_list.popleft()

            node_id: Any = self._get_node_id(item_data)
            if node_id is None:
                visitor(item_data, visitor_context)
                continue
            if node_id in visited:
                visitor(item_data, visitor_context)
                continue
            visited.add(node_id)

            visit_ret = visitor(item_data, visitor_context)
            if visit_ret is None or visit_ret is True:
                self._add_subnodes(item_data)

    # 'item_data' -- data returned by visitor
    def _get_node_id(self, item_data) -> Any:
        raise RuntimeError("not implemented")

    # 'item_data' -- data returned by visitor
    def _add_subnodes(self, item_data):
        raise RuntimeError("not implemented")


class GraphNodeContainer:
    def __init__(self):
        self.container = []

    def collect(self, item_data, _context):
        ancestors_list = item_data[0]
        node = ancestors_list[-1]
        level = len(ancestors_list) - 1
        self.container.append((node, level, item_data))
        return True


## get list of items using given traversal strategy
def get_nodes_from_graph(node, traversal: GraphAbstractTraversal):
    container = GraphNodeContainer()
    traversal.visit_graph(node, container.collect)
    return container.container


# ===========================================================


# traverse tree
class TreeAbstractTraversal:
    def visit_tree(self, item, visitor, visitor_context=None, bottom_top=False):
        if bottom_top:
            self._visit_bottom_top(item, visitor, visitor_context)
        else:
            self._visit_top_bottom(item, visitor, visitor_context)

    def _visit_top_bottom(self, item, visitor, visitor_context=None):
        raise NotImplementedError()

    def _visit_bottom_top(self, item, visitor, visitor_context=None):
        raise NotImplementedError()


# traverse tree
class DepthFirstTreeTraversal(TreeAbstractTraversal):
    def _visit_top_bottom(self, item, visitor, visitor_context=None):
        visit_list = deque([([item], None)])
        while visit_list:
            # 'ancestors_list' - list of ancestors including current item
            # 'item_data' - defined in implementation of 'self._get_subnodes'
            ancestors_list, item_data = visit_list.popleft()
            visit_ret = visitor(ancestors_list, item_data, visitor_context)
            if visit_ret is None or visit_ret is True:
                sub_list = self._get_subnodes(ancestors_list)
                if sub_list:
                    rev_list = reversed(sub_list)
                    visit_list.extendleft(rev_list)

    def _visit_bottom_top(self, item, visitor, visitor_context=None):
        visit_list = deque([([item], None)])
        expanded = set()
        while visit_list:
            # 'ancestors_list' - list of ancestors including current item
            # 'item_data' - defined in implementation of 'self._get_subnodes'
            ancestors_list, item_data = visit_list[0]
            curr_item = ancestors_list[-1]
            curr_id = id(curr_item)
            if curr_id in expanded:
                # leaf found
                visitor(ancestors_list, item_data, visitor_context)
                visit_list.popleft()
                continue
            sub_list = self._get_subnodes(ancestors_list)
            if sub_list:
                rev_list = reversed(sub_list)
                visit_list.extendleft(rev_list)
            expanded.add(curr_id)

    def _get_subnodes(self, ancestors_list):
        raise NotImplementedError()


# traverse tree
class BreadthFirstTreeTraversal(TreeAbstractTraversal):
    def _visit_top_bottom(self, item, visitor, visitor_context=None):
        visit_list = deque([([item], None)])
        while visit_list:
            # 'ancestors_list' - list of ancestors including current item
            # 'item_data' - defined in implementation of 'self._get_subnodes'
            ancestors_list, item_data = visit_list.popleft()
            visit_ret = visitor(ancestors_list, item_data, visitor_context)
            if visit_ret is None or visit_ret is True:
                sub_list = self._get_subnodes(ancestors_list)
                if sub_list:
                    visit_list.extend(sub_list)

    def _visit_bottom_top(self, item, visitor, visitor_context=None):
        root_item = ([item], None)
        visit_list = deque([root_item])
        levels_dict = {0: [root_item]}
        while visit_list:
            # 'ancestors_list' - list of ancestors including current item
            # 'item_data' - defined in implementation of 'self._get_subnodes'
            ancestors_list, item_data = visit_list.popleft()
            sub_list = self._get_subnodes(ancestors_list)
            if sub_list:
                curr_level = len(ancestors_list)
                sub_level_list = levels_dict.get(curr_level, [])
                sub_level_list.extend(sub_list)
                levels_dict[curr_level] = sub_level_list

                visit_list.extend(sub_list)

        rev_order = sorted(levels_dict.keys(), reverse=True)
        for key in rev_order:
            level_list = levels_dict[key]
            for level_item in level_list:
                ancestors_list, item_data = level_item
                visitor(ancestors_list, item_data, visitor_context)

    def _get_subnodes(self, ancestors_list):
        raise NotImplementedError()


class TreeNodeContainer:
    def __init__(self):
        self.container = []

    def collect(self, ancestors_list, _item_data, _context):
        item = ancestors_list[-1]
        level = len(ancestors_list) - 1
        self.container.append((item, level))

    def collect_ancestors(self, ancestors_list, _item_data, _context):
        self.container.append(ancestors_list)
        return True


def get_nodes_from_tree(item: Any, traversal: TreeAbstractTraversal, bottom_top=False) -> List[Tuple[Any, int]]:
    container = TreeNodeContainer()
    traversal.visit_tree(item, container.collect, bottom_top=bottom_top)
    return container.container


def get_nodes_from_tree_ancestors(item: Any, traversal: TreeAbstractTraversal, bottom_top=False) -> List[List[Any]]:
    container = TreeNodeContainer()
    traversal.visit_tree(item, container.collect_ancestors, bottom_top=bottom_top)
    return container.container


# ===========================================================


TreeNode = namedtuple("TreeNode", ["data", "items"])


class NodeTreeDepthFirstIterator:

    def __init__(self, node: TreeNode, bottom_top=False):
        self.first_step = True
        self.visit_list = deque([[node]])
        self.bottom_top = bottom_top
        self.visited: Set[int] = set()
        self.expanded: Set[int] = set()
        if self.bottom_top:
            self._expand()

    def __bool__(self):
        return bool(self.visit_list)

    def current(self) -> TreeNode:
        if not self.visit_list:
            return None
        ancestors_list = self.visit_list[0]
        curr_node = ancestors_list[-1]
        return curr_node

    def skip(self):
        self.visit_list.popleft()

    def get_all(self):
        ret_list = []
        while True:
            next_node = self.next()
            if next_node is None:
                break
            ret_list.append(next_node)
        return ret_list

    def next(self) -> TreeNode:
        if self.first_step:
            node = self.current()
            self.first_step = False
            return node

        if not self.bottom_top:
            return self._next_top_bottom()
        return self._next_bottom_top()

    def _next_top_bottom(self) -> TreeNode:
        while self.visit_list:
            # 'ancestors_list' - list of ancestors including current item
            ancestors_list = self.visit_list.popleft()
            curr_node: TreeNode = ancestors_list[-1]
            curr_id = id(curr_node)
            if curr_id in self.visited:
                continue
            self.visited.add(curr_id)
            self._extendleft(ancestors_list)
            return self.current()
        return None

    def _next_bottom_top(self) -> TreeNode:
        while self.visit_list:
            # 'ancestors_list' - list of ancestors including current item
            self.visit_list.popleft()
            if not self.visit_list:
                break
            self._expand()
            return self.current()
        return None

    def _expand(self):
        while self.visit_list:
            # 'ancestors_list' - list of ancestors including current item
            ancestors_list = self.visit_list[0]
            curr_node = ancestors_list[-1]
            curr_id = id(curr_node)
            if curr_id in self.expanded:
                # leaf found
                return
            self._extendleft(ancestors_list)
            self.expanded.add(curr_id)

    def _extendleft(self, ancestors_list):
        curr_node = ancestors_list[-1]
        sub_items = []
        for subitem in curr_node.items:
            sub_items.append(ancestors_list + [subitem])
        if sub_items:
            rev_list = reversed(sub_items)
            self.visit_list.extendleft(rev_list)


class NodeTreeDepthFirstTraversal(DepthFirstTreeTraversal):
    def _get_subnodes(self, ancestors_list: List[TreeNode]):
        curr_node: TreeNode = ancestors_list[-1]
        ret_list = []
        for subnode in curr_node.items:
            ret_list.append((ancestors_list + [subnode], None))
        return ret_list

    @classmethod
    def traverse(cls, node: TreeNode, visitor, visitor_context=None):
        traversal = cls()
        traversal.visit_tree(node, visitor, visitor_context)

    @classmethod
    def to_list(cls, node: TreeNode, bottom_top=False):
        traversal = cls()
        return get_nodes_from_tree(node, traversal, bottom_top=bottom_top)


class NodeTreeBreadthFirstTraversal(BreadthFirstTreeTraversal):
    def _get_subnodes(self, ancestors_list):
        curr_node: TreeNode = ancestors_list[-1]
        ret_list = []
        for subnode in curr_node.items:
            ret_list.append((ancestors_list + [subnode], None))
        return ret_list

    @classmethod
    def traverse(cls, node: TreeNode, visitor):
        traversal = cls()
        traversal.visit_tree(node, visitor)

    @classmethod
    def to_list(cls, node: TreeNode, bottom_top=False):
        traversal = cls()
        return get_nodes_from_tree(node, traversal, bottom_top=bottom_top)


def print_node_tree(node_tree: TreeNode, indent=2) -> str:
    ret_content = ""
    nodes_list = NodeTreeDepthFirstTraversal.to_list(node_tree)
    for curr_item, level in nodes_list:
        spaces = " " * level * indent
        ret_content += f"{spaces}node data: {curr_item.data} items num: {len(curr_item.items)}\n"
    return ret_content


# ===========================================================


class DictGraphDepthFirstTraversal(GraphAbstractTraversal):
    def visit_graph(self, node, visitor, visitor_context=None):
        return self._visit_graph(([node], None), visitor, visitor_context)

    def _get_node_id(self, item_data) -> str:
        ancestors_list = item_data[0]
        item = ancestors_list[-1]
        if not isinstance(item, dict):
            return None
        return str(id(item))

    def _add_subnodes(self, item_data):
        ancestors_list = item_data[0]
        data_dict = ancestors_list[-1]
        sub_items = []
        for key, subdict in sorted(data_dict.items()):
            sub_items.append((ancestors_list + [subdict], key))
        rev_list = reversed(sub_items)
        self.visit_list.extendleft(rev_list)

    @classmethod
    def traverse(cls, item, visitor):
        traversal = cls()
        traversal.visit_graph(item, visitor)

    @classmethod
    def to_list(cls, item):
        traversal = cls()
        return get_nodes_from_graph(item, traversal)


# convert dict graph to dict tree
class DictToTreeConverter:

    def __init__(self):
        self.node_dict = {}

    def convert(self, data_dict) -> TreeNode:
        container_node = TreeNode(None, [])
        self.node_dict[""] = container_node
        traversal = DictGraphDepthFirstTraversal()
        traversal.visit_graph(data_dict, self.visit_item)

        root_list = container_node.items
        if len(root_list) != 1:
            raise RuntimeError("error while converting entry graph")

        top_item = root_list[0]
        if len(top_item.items) == 1:
            top_item = top_item.items[0]
        return top_item

    def visit_item(self, item_data, _context=None):
        ancestors_list = item_data[0]
        dict_key = item_data[1]
        parents_list = ancestors_list[:-1]
        parent_node_id = self._get_id_path(parents_list)
        parent_node = self.node_dict[parent_node_id]

        node = ancestors_list[-1]
        new_node = TreeNode((dict_key, node), [])
        parent_node.items.append(new_node)

        if isinstance(node, dict):
            entry_node_id = self._get_id_path(ancestors_list)
            self.node_dict[entry_node_id] = new_node
        return True

    def _get_id_path(self, ancestors_list):
        return "".join([str(id(item)) for item in ancestors_list])


def create_tree_from_dict(entry) -> TreeNode:
    converter = DictToTreeConverter()
    return converter.convert(entry)
