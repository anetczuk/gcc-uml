#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest
from typing import Dict, Any

from gccuml.abstracttraversal import (
    create_tree_from_dict,
    NodeTreeDepthFirstTraversal,
    NodeTreeBreadthFirstTraversal,
    TreeNode,
    get_nodes_from_tree,
    get_nodes_from_tree_ancestors,
    NodeTreeDepthFirstIterator,
)


class AbstractTraversalTest(unittest.TestCase):

    def test_create_tree_from_dict(self):
        data = {1: {11: 101, 12: 102}, 2: {21: 201, 22: 202}}
        tree = create_tree_from_dict(data)

        self.assertEqual(None, tree.data[0])
        self.assertEqual(2, len(tree.items))

        subnode = tree.items[0]
        self.assertEqual(1, subnode.data[0])
        self.assertEqual(2, len(subnode.items))

        subnode = subnode.items[1]
        self.assertEqual(12, subnode.data[0])
        self.assertEqual(0, len(subnode.items))

    def test_create_tree_from_dict_recursive(self):
        data: Dict[int, Any] = {1: {11: 101, 12: 102}, 2: {21: 201, 22: 202}, 3: None}
        data[3] = data  # make recursive
        tree = create_tree_from_dict(data)

        self.assertEqual(None, tree.data[0])
        self.assertEqual(3, len(tree.items))

        subnode = tree.items[0]
        self.assertEqual(1, subnode.data[0])
        self.assertEqual(2, len(subnode.items))

        subnode = tree.items[2]
        self.assertEqual(3, subnode.data[0])
        self.assertDictEqual(data, subnode.data[1])  # check recursive
        self.assertEqual(0, len(subnode.items))  # do not expand already handled object


class NodeTreeDepthFirstIteratorTest(unittest.TestCase):

    def test_get_list_topbottom(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        iterator = NodeTreeDepthFirstIterator(tree, bottom_top=False)
        nodes = iterator.get_all()
        nodes_keys = [item.data[0] for item in nodes]
        self.assertEqual([1, 11, 111, 112, 12, 121], nodes_keys)

    def test_get_list_bottomtop(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        iterator = NodeTreeDepthFirstIterator(tree, bottom_top=True)
        nodes = iterator.get_all()
        nodes_keys = [item.data[0] for item in nodes]
        self.assertEqual([111, 112, 11, 121, 12, 1], nodes_keys)


class NodeTreeDepthFirstTraversalTest(unittest.TestCase):

    def test_get_nodes_from_tree(self):
        data = {1: {11: 101, 12: 102}, 2: {21: 201, 22: 202}, 3: None}
        tree: TreeNode = create_tree_from_dict(data)

        traversal = NodeTreeDepthFirstTraversal()
        nodes_list = get_nodes_from_tree(tree, traversal)

        self.assertEqual(8, len(nodes_list))
        node_tuple = nodes_list[1]
        self.assertEqual(tuple, type(node_tuple))
        self.assertEqual(2, len(node_tuple))
        self.assertEqual(TreeNode, type(node_tuple[0]))
        self.assertEqual(1, node_tuple[1])

    def test_get_nodes_from_tree_ancestors(self):
        data = {1: {11: 101, 12: 102}, 2: {21: 201, 22: 202}, 3: None}
        tree: TreeNode = create_tree_from_dict(data)

        traversal = NodeTreeDepthFirstTraversal()
        nodes_list = get_nodes_from_tree_ancestors(tree, traversal)

        self.assertEqual(8, len(nodes_list))
        node_ancestors = nodes_list[1]
        self.assertEqual(list, type(node_ancestors))
        self.assertEqual(2, len(node_ancestors))
        self.assertEqual(TreeNode, type(node_ancestors[1]))

    def test_to_list_topbottom(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        nodes = NodeTreeDepthFirstTraversal.to_list(tree)
        nodes_keys = [item[0].data[0] for item in nodes]
        self.assertEqual([1, 11, 111, 112, 12, 121], nodes_keys)

    def test_to_list_bottomtop(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        nodes = NodeTreeDepthFirstTraversal.to_list(tree, bottom_top=True)
        nodes_keys = [item[0].data[0] for item in nodes]
        self.assertEqual([111, 112, 11, 121, 12, 1], nodes_keys)


class NodeTreeBreadthFirstTraversalTest(unittest.TestCase):

    def test_to_list_topbottom(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        nodes = NodeTreeBreadthFirstTraversal.to_list(tree)
        nodes_keys = [item[0].data[0] for item in nodes]
        self.assertEqual([1, 11, 12, 111, 112, 121], nodes_keys)

    def test_to_list_bottomtop(self):
        data = {1: {11: {111: 101, 112: 102}, 12: {121: 103}}}
        tree = create_tree_from_dict(data)

        nodes = NodeTreeBreadthFirstTraversal.to_list(tree, bottom_top=True)
        nodes_keys = [item[0].data[0] for item in nodes]
        self.assertEqual([111, 112, 121, 11, 12, 1], nodes_keys)
