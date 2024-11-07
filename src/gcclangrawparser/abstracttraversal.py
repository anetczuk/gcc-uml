#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
from collections import deque


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# traverse graph
class GraphAbstractTraversal:
    def __init__(self):
        self.visit_list = None
        self.visited = set()

    def visit_graph(self, node, visitor, visitor_context=None):
        self.visit_list = deque([([node], None)])
        self.visited = set()
        while self.visit_list:
            # 'family_list' - list of ancestors including current node
            family_list, node_data = self.visit_list.popleft()
            curr_node = family_list[-1]
            node_id = self._get_node_id(curr_node)
            if node_id is None:
                visitor(family_list, node_data, visitor_context)
                continue
            if node_id in self.visited:
                visitor(family_list, node_data, visitor_context)
                continue
            self.visited.add(node_id)
            if visitor(family_list, node_data, visitor_context):
                self._add_subnodes(family_list)

    def _add_subnodes(self, family_list):
        raise RuntimeError("not implemented")

    def _get_node_id(self, node) -> str:
        raise RuntimeError("not implemented")


class GraphNodeContainer:
    def __init__(self):
        self.container = []

    def collect(self, family_list, node_data, _context):
        node = family_list[-1]
        level = len(family_list) - 1
        self.container.append((node, level, node_data))
        return True


def get_nodes_from_graph(node, traversal: GraphAbstractTraversal):
    container = GraphNodeContainer()
    traversal.visit_graph(node, container.collect)
    return container.container


# ===========================================================


# traverse tree
class TreeAbstractTraversal:
    def __init__(self):
        self.visit_list = None

    def visit_tree(self, node, visitor, visitor_context=None):
        self.visit_list = deque([([node], None)])
        while self.visit_list:
            # 'family_list' - list of ancestors including current node
            family_list, node_data = self.visit_list.popleft()
            if visitor(family_list, node_data, visitor_context):
                self._add_subnodes(family_list)

    def _add_subnodes(self, family_list):
        raise RuntimeError("not implemented")


class TreeNodeContainer:
    def __init__(self):
        self.container = []

    def collect(self, family_list, node_data, _context):
        node = family_list[-1]
        level = len(family_list) - 1
        self.container.append((node, level, node_data))
        return True


def get_nodes_from_tree(node, traversal: TreeAbstractTraversal):
    container = TreeNodeContainer()
    traversal.visit_tree(node, container.collect)
    return container.container
